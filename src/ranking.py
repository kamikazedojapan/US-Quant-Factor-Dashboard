"""Ranking multifatorial diário da Home, com calendário e snapshot de segurança."""

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from src.data_loader import download_market_data, get_sp500_tickers
from src.factors import calculate_price_volume_factor_scores

LOGGER = logging.getLogger(__name__)
DEFAULT_SNAPSHOT_PATH = (
  Path(__file__).resolve().parent.parent
  / "data" / "cache" / "home_ranking_latest.json"
)
SNAPSHOT_VERSION = 1
MINIMUM_HISTORY = 253
MINIMUM_VOLUME_HISTORY = 60
# Incrementar ao mudar os fatores/critério de elegibilidade/scoring.
HOME_RANKING_ALGORITHM_VERSION = 1


def _ranking_spec(benchmark="SPY", lookback_months=18,
                  momentum_weight=40, risk_weight=35, liquidity_weight=25):
  """Identificador explícito da metodologia que gerou o snapshot."""
  return (
    f"v{HOME_RANKING_ALGORITHM_VERSION}|{benchmark}|{lookback_months}|"
    f"{momentum_weight}|{risk_weight}|{liquidity_weight}"
  )


def _universe_fingerprint(stocks_df):
  """Hash do conjunto de tickers; detecta alteração do universo sem baixar preços."""
  if "ticker" not in stocks_df.columns:
    raise ValueError("Universo sem coluna ticker")
  tickers = (
    stocks_df["ticker"].astype("string").str.upper().str.strip().dropna()
  )
  tickers = sorted({value for value in tickers.tolist() if value})
  if not tickers:
    raise ValueError("Universo sem tickers")
  return hashlib.sha256("\n".join(tickers).encode("utf-8")).hexdigest()


class RankingUnavailableError(RuntimeError):
  """Falha ao obter dados atuais e ausência de um snapshot recuperável."""


def get_latest_complete_nyse_session(now=None, grace_minutes=15):
  """Última sessão encerrada da NYSE, incluindo feriados e fechamentos antecipados.

  A margem de segurança evita consultar o fechamento logo no minuto em que
  o pregão termina e o fornecedor pode ainda estar consolidando os dados.
  """
  if grace_minutes < 0:
    raise ValueError("grace_minutes não pode ser negativo.")

  now_utc = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
  if now_utc.tzinfo is None:
    raise ValueError("now precisa conter informação de fuso horário.")
  now_utc = now_utc.tz_convert("UTC")

  trading_date = now_utc.tz_convert("America/New_York").date()
  calendar = xcals.get_calendar(
    "XNYS",
    start=trading_date - pd.Timedelta(days=15),
    end=trading_date + pd.Timedelta(days=3),
  )
  session = calendar.date_to_session(
    pd.Timestamp(trading_date), direction="previous"
  )
  close_utc = calendar.session_close(session)
  if now_utc < close_utc + pd.Timedelta(minutes=grace_minutes):
    session = calendar.previous_session(session)
  return pd.Timestamp(session).tz_localize(None).normalize()


def _normalize_daily_frame(frame):
  """Converte timestamps diários de mercado em datas locais sem fuso."""
  result = frame.copy()
  if not isinstance(result.index, pd.DatetimeIndex):
    raise ValueError("Os dados de mercado devem ter índice de datas.")
  if result.index.tz is not None:
    result.index = result.index.tz_convert("America/New_York").tz_localize(None)
  result.index = result.index.normalize()
  return result.sort_index().groupby(level=0).last()


def build_latest_multifactor_ranking(
  prices,
  volumes,
  stocks_df,
  benchmark="SPY",
  top_n=10,
  momentum_weight=40,
  risk_weight=35,
  liquidity_weight=25,
):
  """Reutiliza a mesma função de scoring que atende as outras páginas."""
  if top_n <= 0:
    raise ValueError("top_n deve ser maior do que zero.")
  if "ticker" not in stocks_df.columns:
    raise ValueError("stocks deve conter a coluna 'ticker'.")

  factor_scores = calculate_price_volume_factor_scores(
    prices=prices,
    volumes=volumes,
    benchmark=benchmark,
    momentum_weight=momentum_weight,
    risk_weight=risk_weight,
    liquidity_weight=liquidity_weight,
  )
  ranking = factor_scores.drop(index=benchmark, errors="ignore").dropna(
    subset=["score_preliminar"]
  ).copy()
  ranking.index.name = "ticker"
  ranking = ranking.reset_index()
  ranking = ranking[ranking["ticker"].isin(stocks_df["ticker"])].copy()
  ranking.insert(0, "rank", range(1, len(ranking) + 1))

  metadata_columns = [
    column for column in ("ticker", "company", "sector", "industry")
    if column in stocks_df.columns
  ]
  metadata = stocks_df[metadata_columns].drop_duplicates(subset=["ticker"])
  ranking = ranking.merge(metadata, on="ticker", how="left", sort=False)
  return ranking.head(top_n).copy()


def load_latest_multifactor_ranking(
  max_top_n=50,
  benchmark="SPY",
  lookback_months=18,
  momentum_weight=40,
  risk_weight=35,
  liquidity_weight=25,
):
  """Calcula o Top N da última sessão completa, sem ativos desatualizados."""
  if max_top_n <= 0:
    raise ValueError("max_top_n deve ser maior que zero.")
  if lookback_months <= 0:
    raise ValueError("lookback_months deve ser maior que zero.")

  stocks_df = get_sp500_tickers()
  if stocks_df.empty:
    raise ValueError("O universo de ações está vazio.")
  if "ticker" not in stocks_df.columns:
    raise ValueError("O universo deve conter a coluna 'ticker'.")

  stocks_df = stocks_df.copy()
  stocks_df["ticker"] = stocks_df["ticker"].astype("string").str.upper().str.strip()
  stocks_df = stocks_df.dropna(subset=["ticker"])
  stocks_df = stocks_df[stocks_df["ticker"].ne("")].drop_duplicates("ticker")
  tickers = [ticker for ticker in stocks_df["ticker"].tolist() if ticker != benchmark]
  if not tickers:
    raise ValueError("Não há ações disponíveis no universo de ranking.")

  completed_session = get_latest_complete_nyse_session()
  # yfinance trata end como EXCLUSIVO; incluir o dia seguinte ao pregão.
  exclusive_end = completed_session + pd.Timedelta(days=1)
  start_date = exclusive_end - pd.DateOffset(months=lookback_months)
  download_tickers = tickers + [benchmark]

  prices, volumes = download_market_data(
    tickers=download_tickers,
    start_date=start_date,
    end_date=exclusive_end,
  )
  if prices.empty:
    raise ValueError("Não foi possível obter dados de mercado.")
  if benchmark not in prices.columns:
    raise ValueError(f"O benchmark {benchmark} não foi encontrado.")

  prices = _normalize_daily_frame(prices).loc[:completed_session]
  volumes = _normalize_daily_frame(volumes).reindex(
    index=prices.index, columns=prices.columns
  )
  benchmark_prices = pd.to_numeric(prices[benchmark], errors="coerce").dropna()
  if benchmark_prices.empty:
    raise ValueError(f"O benchmark {benchmark} não possui dados válidos.")
  market_date = benchmark_prices.index.max()
  if market_date != completed_session:
    raise ValueError(
      f"O benchmark não possui a sessão completa de {completed_session.date()}."
    )
  if benchmark_prices.gt(0).sum() < MINIMUM_HISTORY:
    raise ValueError("O SPY não tem histórico suficiente para o scoring.")

  # Os dias de SPY definem o calendário diário a ser usado em todos os ativos.
  # Isso impede que linhas esparsas de outros fornecedores distorçam os retornos.
  prices = prices.loc[benchmark_prices.index].copy()
  volumes = volumes.reindex(index=prices.index, columns=prices.columns)

  # Evita que NaNs na última sessão formem rankings com preços obsoletos.
  eligible = []
  for ticker in tickers:
    if ticker not in prices.columns or ticker not in volumes.columns:
      continue
    asset_prices = pd.to_numeric(prices[ticker], errors="coerce")
    asset_volumes = pd.to_numeric(volumes[ticker], errors="coerce")
    valid_prices = asset_prices.replace([np.inf, -np.inf], np.nan).gt(0)
    valid_volumes = asset_volumes.replace([np.inf, -np.inf], np.nan).gt(0)
    if (
      bool(valid_prices.loc[market_date])
      and bool(valid_volumes.loc[market_date])
      and len(valid_prices) >= MINIMUM_HISTORY
      and bool(valid_prices.tail(MINIMUM_HISTORY).all())
      and len(valid_volumes) >= MINIMUM_VOLUME_HISTORY
      and bool(valid_volumes.tail(MINIMUM_VOLUME_HISTORY).all())
    ):
      eligible.append(ticker)

  if not eligible:
    raise ValueError("Nenhuma ação com cotação e volume atualizados está elegível.")

  # Aplica scoring a todos os ativos elegíveis simultaneamente; não recalcula
  # percentis sobre o Top 10/20/50, o que modificaria os scores exibidos.
  score_prices = prices[eligible + [benchmark]].copy()
  score_volumes = volumes.reindex(index=score_prices.index, columns=score_prices.columns)
  full_ranking = build_latest_multifactor_ranking(
    prices=score_prices,
    volumes=score_volumes,
    stocks_df=stocks_df,
    benchmark=benchmark,
    top_n=len(eligible),
    momentum_weight=momentum_weight,
    risk_weight=risk_weight,
    liquidity_weight=liquidity_weight,
  )
  if full_ranking.empty:
    raise ValueError("Nenhuma ação elegível foi encontrada para o ranking.")

  ranking = full_ranking.head(max_top_n).copy()
  info = {
    "as_of_date": market_date,
    "universe_size": len(tickers),
    "eligible_count": len(full_ranking),
    "returned_count": len(ranking),
    "universe_fingerprint": _universe_fingerprint(stocks_df),
    "ranking_spec": _ranking_spec(
      benchmark, lookback_months, momentum_weight, risk_weight, liquidity_weight
    ),
    "source": "live",
  }
  return ranking, info


def save_ranking_snapshot(ranking, ranking_info, path=DEFAULT_SNAPSHOT_PATH):
  """Grava ranking e metadados em um único JSON, com substituição atômica."""
  if ranking.empty or "as_of_date" not in ranking_info:
    raise ValueError("O snapshot exige ranking e data de referência válidos.")
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  metadata = {
    "as_of_date": pd.Timestamp(ranking_info["as_of_date"]).date().isoformat(),
    "universe_size": int(ranking_info["universe_size"]),
    "eligible_count": int(ranking_info["eligible_count"]),
    "returned_count": int(len(ranking)),
  }
  for key in ("universe_fingerprint", "ranking_spec"):
    if key in ranking_info:
      metadata[key] = ranking_info[key]
  payload = {
    "version": SNAPSHOT_VERSION,
    "ranking": json.loads(ranking.to_json(orient="records", date_format="iso")),
    "info": metadata,
  }
  temporary_name = None
  try:
    with tempfile.NamedTemporaryFile(
      mode="w", encoding="utf-8", dir=path.parent,
      prefix=".home_ranking_", suffix=".tmp", delete=False,
    ) as file:
      temporary_name = file.name
      json.dump(payload, file, ensure_ascii=False, allow_nan=False)
      file.flush()
      os.fsync(file.fileno())
    os.replace(temporary_name, path)
  finally:
    if temporary_name and os.path.exists(temporary_name):
      os.unlink(temporary_name)


def load_ranking_snapshot(path=DEFAULT_SNAPSHOT_PATH):
  """Recupera um snapshot válido; arquivos ausentes/corrompidos são ignorados."""
  try:
    with Path(path).open("r", encoding="utf-8") as file:
      payload = json.load(file)
    if not isinstance(payload, dict) or payload.get("version") != SNAPSHOT_VERSION:
      return None
    if not isinstance(payload.get("ranking"), list):
      return None
    if not isinstance(payload.get("info"), dict):
      return None
    ranking = pd.DataFrame(payload["ranking"])
    info = dict(payload["info"])
    required = {"rank", "ticker", "score_preliminar"}
    if ranking.empty or not required.issubset(ranking.columns):
      return None
    if ranking["ticker"].isna().any() or ranking["ticker"].duplicated().any():
      return None
    scores = pd.to_numeric(ranking["score_preliminar"], errors="coerce")
    if scores.isna().any():
      return None
    info["as_of_date"] = pd.Timestamp(info["as_of_date"])
    if pd.isna(info["as_of_date"]):
      return None
    if info.get("returned_count") != len(ranking):
      return None
    return ranking, info
  except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
    return None


def _is_current_home_snapshot(ranking, info, max_top_n):
  """Snapshot reutilizável apenas quando data, universo e metodologia coincidem.

  Snapshots legados, sem fingerprint/spec, permanecem disponíveis SOMENTE como
  fallback com aviso de dados antigos (nunca como ranking atual garantido).
  """
  try:
    if max_top_n <= 0:
      return False
    if pd.Timestamp(info["as_of_date"]) != get_latest_complete_nyse_session():
      return False
    if info.get("ranking_spec") != _ranking_spec():
      return False
    if info.get("universe_fingerprint") != _universe_fingerprint(get_sp500_tickers()):
      return False
    eligible_count = int(info["eligible_count"])
    if eligible_count <= 0 or len(ranking) < min(max_top_n, eligible_count):
      return False
    return True
  except (ValueError, KeyError, TypeError, AttributeError, OSError):
    return False


def load_home_ranking_with_fallback(
  max_top_n=50,
  snapshot_path=DEFAULT_SNAPSHOT_PATH,
  force_refresh=False,
):
  """Reusa snapshot atual; recalcula ao trocar sessão/universo ou forçar refresh.

  Falhas de atualização usam o último snapshot, inclusive antigo, com aviso.
  """
  if max_top_n <= 0:
    raise ValueError("max_top_n deve ser maior que zero.")

  if not force_refresh:
    saved = load_ranking_snapshot(snapshot_path)
    if saved is not None and _is_current_home_snapshot(*saved, max_top_n):
      cached_ranking, cached_info = saved
      cached_info["source"] = "snapshot_current"
      result = cached_ranking.head(max_top_n).copy()
      cached_info["returned_count"] = len(result)
      return result, cached_info

  try:
    ranking, info = load_latest_multifactor_ranking(max_top_n=max_top_n)
  except Exception as error:
    LOGGER.warning("Falha ao atualizar o ranking; tentando snapshot: %s", error)
    saved = load_ranking_snapshot(snapshot_path)
    if saved is None:
      raise RankingUnavailableError(
        "Não foi possível atualizar o ranking e não há ranking salvo disponível."
      ) from error
    saved_ranking, saved_info = saved
    saved_info["source"] = "snapshot"
    saved_info["update_error_type"] = type(error).__name__
    return saved_ranking.head(max_top_n).copy(), saved_info

  try:
    save_ranking_snapshot(ranking, info, snapshot_path)
  except (OSError, ValueError, TypeError) as error:
    LOGGER.warning("Não foi possível persistir o ranking da Home: %s", error)
    info["snapshot_save_failed"] = True
  return ranking, info
