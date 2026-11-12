"""Testes para ranking de Home: scoring, último pregão, elegibilidade e fallback."""
from datetime import date

import pandas as pd
import pytest

from src.ranking import (
  RankingUnavailableError,
  build_latest_multifactor_ranking,
  get_latest_complete_nyse_session,
  load_home_ranking_with_fallback,
  load_latest_multifactor_ranking,
  load_ranking_snapshot,
  save_ranking_snapshot,
)


def build_mock_factor_scores(size=60):
  tickers = [f"TEST{i:02d}" for i in range(size)]
  return pd.DataFrame(
    {
      "score_momentum": range(size, 0, -1),
      "score_risco": range(size, 0, -1),
      "score_liquidez": range(size, 0, -1),
      "score_preliminar": range(size, 0, -1),
    },
    index=tickers,
  )


def build_mock_stocks_df(size=60):
  return pd.DataFrame(
    {
      "ticker": [f"TEST{i:02d}" for i in range(size)],
      "company": [f"Company {i}" for i in range(size)],
      "sector": ["Technology"] * size,
      "industry": ["Software"] * size,
    }
  )


def build_daily_market_data(size=3, end="2026-09-30", periods=260):
  dates = pd.bdate_range(end=end, periods=periods)
  data = {
    f"TEST{i:02d}": range(100 + i, 100 + i + periods)
    for i in range(size)
  }
  data["SPY"] = range(500, 500 + periods)
  prices = pd.DataFrame(data, index=dates)
  volumes = pd.DataFrame(1000.0, index=dates, columns=prices.columns)
  return prices, volumes


def setup_daily_mock(monkeypatch, prices, volumes, size=3, completed="2026-09-30"):
  monkeypatch.setattr("src.ranking.get_sp500_tickers", lambda: build_mock_stocks_df(size))
  monkeypatch.setattr("src.ranking.download_market_data", lambda **kwargs: (prices, volumes))
  monkeypatch.setattr(
    "src.ranking.get_latest_complete_nyse_session",
    lambda: pd.Timestamp(completed),
  )


@pytest.mark.parametrize("top_n", [10, 20, 50])
def test_build_latest_ranking_respects_top_n(monkeypatch, top_n):
  monkeypatch.setattr(
    "src.ranking.calculate_price_volume_factor_scores",
    lambda **kwargs: build_mock_factor_scores(),
  )
  ranking = build_latest_multifactor_ranking(
    prices=pd.DataFrame(), volumes=pd.DataFrame(),
    stocks_df=build_mock_stocks_df(), top_n=top_n,
  )
  assert len(ranking) == top_n
  assert ranking["rank"].tolist() == list(range(1, top_n + 1))


def test_build_latest_ranking_returns_only_available_assets(monkeypatch):
  monkeypatch.setattr(
    "src.ranking.calculate_price_volume_factor_scores",
    lambda **kwargs: build_mock_factor_scores(size=15),
  )
  ranking = build_latest_multifactor_ranking(
    prices=pd.DataFrame(), volumes=pd.DataFrame(),
    stocks_df=build_mock_stocks_df(size=15), top_n=50,
  )
  assert len(ranking) == 15


def test_build_latest_ranking_rejects_invalid_top_n():
  with pytest.raises(ValueError, match="top_n deve ser maior do que zero"):
    build_latest_multifactor_ranking(
      prices=pd.DataFrame(), volumes=pd.DataFrame(),
      stocks_df=pd.DataFrame({"ticker": []}), top_n=0,
    )


def test_build_latest_ranking_adds_stock_metadata(monkeypatch):
  monkeypatch.setattr(
    "src.ranking.calculate_price_volume_factor_scores",
    lambda **kwargs: build_mock_factor_scores(size=3),
  )
  ranking = build_latest_multifactor_ranking(
    prices=pd.DataFrame(), volumes=pd.DataFrame(),
    stocks_df=build_mock_stocks_df(size=3), top_n=3,
  )
  assert {"company", "sector", "industry"}.issubset(ranking.columns)
  assert ranking.iloc[0]["ticker"] == "TEST00"
  assert ranking.iloc[0]["company"] == "Company 0"


def test_load_latest_ranking_uses_latest_benchmark_date(monkeypatch):
  prices, volumes = build_daily_market_data()
  setup_daily_mock(monkeypatch, prices, volumes)
  ranking, info = load_latest_multifactor_ranking(max_top_n=3)
  assert len(ranking) == 3
  assert info["as_of_date"] == pd.Timestamp("2026-09-30")


def test_load_latest_ranking_respects_max_top_n(monkeypatch):
  prices, volumes = build_daily_market_data(size=60)
  setup_daily_mock(monkeypatch, prices, volumes, size=60)
  ranking, info = load_latest_multifactor_ranking(max_top_n=20)
  assert len(ranking) == 20
  assert info["returned_count"] == 20
  assert info["eligible_count"] == 60


def test_load_latest_ranking_rejects_invalid_max_top_n():
  with pytest.raises(ValueError, match="max_top_n deve ser maior que zero"):
    load_latest_multifactor_ranking(max_top_n=0)


def test_load_latest_ranking_requires_benchmark(monkeypatch):
  prices, volumes = build_daily_market_data()
  prices = prices.drop(columns="SPY")
  volumes = volumes.drop(columns="SPY")
  setup_daily_mock(monkeypatch, prices, volumes)
  with pytest.raises(ValueError, match="benchmark SPY não foi encontrado"):
    load_latest_multifactor_ranking()


def test_load_latest_ranking_rejects_empty_universe(monkeypatch):
  monkeypatch.setattr("src.ranking.get_sp500_tickers", lambda: pd.DataFrame())
  with pytest.raises(ValueError, match="O universo de ações está vazio"):
    load_latest_multifactor_ranking()


def test_load_latest_ranking_rejects_empty_market_data(monkeypatch):
  setup_daily_mock(monkeypatch, pd.DataFrame(), pd.DataFrame())
  with pytest.raises(ValueError, match="Não foi possível obter dados de mercado"):
    load_latest_multifactor_ranking()


@pytest.mark.parametrize(
  ("instant", "expected"),
  [
    ("2026-11-11T20:45:00Z", "2026-11-10"),  # ainda em pregão
    ("2026-11-11T21:10:00Z", "2026-11-10"),  # consolidação pós-fechamento
    ("2026-11-11T21:20:00Z", "2026-11-11"),  # sessão encerrada
    ("2026-11-26T19:00:00Z", "2026-11-25"),  # Thanksgiving
    ("2026-11-27T18:10:00Z", "2026-11-25"),  # fechamento antecipado 13h NY
    ("2026-11-27T18:20:00Z", "2026-11-27"),
    ("2026-11-28T20:00:00Z", "2026-11-27"),  # sábado
  ],
)
def test_get_latest_complete_nyse_session(instant, expected):
  assert get_latest_complete_nyse_session(pd.Timestamp(instant)) == pd.Timestamp(expected)


def test_download_includes_completed_session_with_exclusive_end(monkeypatch):
  prices, volumes = build_daily_market_data()
  setup_daily_mock(monkeypatch, prices, volumes)
  captured = {}

  def fake_download(**kwargs):
    captured.update(kwargs)
    return prices, volumes

  monkeypatch.setattr("src.ranking.download_market_data", fake_download)
  load_latest_multifactor_ranking()
  assert captured["end_date"] == pd.Timestamp("2026-10-01")


def test_stale_asset_is_excluded_from_scoring(monkeypatch):
  prices, volumes = build_daily_market_data()
  prices.loc[pd.Timestamp("2026-09-30"), "TEST01"] = float("nan")
  setup_daily_mock(monkeypatch, prices, volumes)
  ranking, info = load_latest_multifactor_ranking()
  assert "TEST01" not in ranking["ticker"].tolist()
  assert info["eligible_count"] == 2


def test_asset_without_latest_volume_is_excluded(monkeypatch):
  prices, volumes = build_daily_market_data()
  volumes.loc[pd.Timestamp("2026-09-30"), "TEST02"] = float("nan")
  setup_daily_mock(monkeypatch, prices, volumes)
  ranking, info = load_latest_multifactor_ranking()
  assert "TEST02" not in ranking["ticker"].tolist()
  assert info["eligible_count"] == 2


def test_asset_with_insufficient_history_is_excluded(monkeypatch):
  prices, volumes = build_daily_market_data()
  prices.loc[prices.index[:30], "TEST00"] = float("nan")
  setup_daily_mock(monkeypatch, prices, volumes)
  ranking, info = load_latest_multifactor_ranking()
  assert "TEST00" not in ranking["ticker"].tolist()
  assert info["eligible_count"] == 2


def test_asset_with_gap_in_recent_sessions_is_excluded(monkeypatch):
  prices, volumes = build_daily_market_data()
  prices.loc[prices.index[-30], "TEST00"] = float("nan")
  setup_daily_mock(monkeypatch, prices, volumes)
  ranking, info = load_latest_multifactor_ranking()
  assert "TEST00" not in ranking["ticker"].tolist()
  assert info["eligible_count"] == 2


def test_stale_spy_rejects_refresh(monkeypatch):
  prices, volumes = build_daily_market_data()
  prices.loc[pd.Timestamp("2026-09-30"), "SPY"] = float("nan")
  setup_daily_mock(monkeypatch, prices, volumes)
  with pytest.raises(ValueError, match="sessão completa"):
    load_latest_multifactor_ranking()


def test_snapshot_roundtrip_and_atomic_file(tmp_path):
  path = tmp_path / "cache" / "home.json"
  ranking = pd.DataFrame(
    {"rank": [1, 2], "ticker": ["AAA", "BBB"], "score_preliminar": [92.5, 90.1]}
  )
  info = {"as_of_date": pd.Timestamp("2026-09-30"), "universe_size": 3, "eligible_count": 2}
  save_ranking_snapshot(ranking, info, path)
  saved_ranking, saved_info = load_ranking_snapshot(path)
  pd.testing.assert_frame_equal(saved_ranking, ranking)
  assert saved_info["as_of_date"] == pd.Timestamp("2026-09-30")
  assert len(list((tmp_path / "cache").glob("*.tmp"))) == 0


def test_snapshot_corrupt_data_is_ignored(tmp_path):
  path = tmp_path / "home.json"
  path.write_text("{not a valid json}", encoding="utf-8")
  assert load_ranking_snapshot(path) is None


def test_fallback_returns_last_good_snapshot(monkeypatch, tmp_path):
  ranking = pd.DataFrame(
    {"rank": [1], "ticker": ["AAA"], "score_preliminar": [92.5]}
  )
  info = {"as_of_date": pd.Timestamp("2026-09-30"), "universe_size": 3, "eligible_count": 1}
  path = tmp_path / "latest.json"
  save_ranking_snapshot(ranking, info, path)

  def fail_refresh(**kwargs):
    raise ConnectionError("API indisponível")

  monkeypatch.setattr("src.ranking.load_latest_multifactor_ranking", fail_refresh)
  fallback, meta = load_home_ranking_with_fallback(snapshot_path=path)
  pd.testing.assert_frame_equal(fallback, ranking)
  assert meta["source"] == "snapshot"
  assert meta["update_error_type"] == "ConnectionError"


def test_failed_refresh_without_snapshot_raises(monkeypatch, tmp_path):
  def fail_refresh(**kwargs):
    raise TimeoutError("API indisponível")

  monkeypatch.setattr("src.ranking.load_latest_multifactor_ranking", fail_refresh)
  with pytest.raises(RankingUnavailableError, match="não há ranking salvo"):
    load_home_ranking_with_fallback(snapshot_path=tmp_path / "missing.json")


def test_successful_refresh_creates_snapshot(monkeypatch, tmp_path):
  ranking = pd.DataFrame(
    {"rank": [1], "ticker": ["AAA"], "score_preliminar": [98.0]}
  )
  info = {"as_of_date": pd.Timestamp("2026-09-30"), "universe_size": 3, "eligible_count": 1}
  monkeypatch.setattr(
    "src.ranking.load_latest_multifactor_ranking",
    lambda **kwargs: (ranking, info),
  )
  path = tmp_path / "cache" / "home.json"
  loaded, loaded_info = load_home_ranking_with_fallback(snapshot_path=path)
  assert loaded_info["as_of_date"] == pd.Timestamp("2026-09-30")
  assert loaded.equals(ranking)
  assert path.exists()
