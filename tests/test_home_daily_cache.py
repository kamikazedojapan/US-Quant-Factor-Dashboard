"""Reuso do snapshot diário: sem rede nos testes (mocks)."""
import pandas as pd
import pytest

from src import ranking as module


def _frame(score=97):
    return pd.DataFrame({
        "rank": [1], "ticker": ["AAA"], "score_preliminar": [float(score)],
    })


def _info(session="2026-11-12", score=None):
    return {
        "as_of_date": pd.Timestamp(session),
        "universe_size": 1,
        "eligible_count": 1,
        "universe_fingerprint": module._universe_fingerprint(
            pd.DataFrame({"ticker": ["AAA"]})
        ),
        "ranking_spec": module._ranking_spec(),
        "source": "live",
    }


def _setup(monkeypatch, counter):
    monkeypatch.setattr(
        module, "get_latest_complete_nyse_session", lambda: pd.Timestamp("2026-11-12")
    )
    monkeypatch.setattr(
        module, "get_sp500_tickers", lambda: pd.DataFrame({"ticker": ["AAA"]})
    )

    def calculate(**kwargs):
        counter["count"] += 1
        return _frame(counter["count"]), _info()

    monkeypatch.setattr(module, "load_latest_multifactor_ranking", calculate)


def test_same_session_uses_snapshot_without_recalculating(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    first, info1 = module.load_home_ranking_with_fallback(snapshot_path=path)
    second, info2 = module.load_home_ranking_with_fallback(snapshot_path=path)
    assert counter["count"] == 1
    assert first.equals(second)
    assert info1["source"] == "live"
    assert info2["source"] == "snapshot_current"


def test_manual_refresh_bypasses_current_snapshot(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    module.load_home_ranking_with_fallback(snapshot_path=path)
    updated, info = module.load_home_ranking_with_fallback(
        snapshot_path=path, force_refresh=True
    )
    assert counter["count"] == 2
    assert updated.iloc[0]["score_preliminar"] == 2.0
    assert info["source"] == "live"
    cached, info2 = module.load_home_ranking_with_fallback(snapshot_path=path)
    assert info2["source"] == "snapshot_current"
    assert cached.iloc[0]["score_preliminar"] == 2.0


def test_stale_snapshot_is_not_reused(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    module.save_ranking_snapshot(_frame(), _info("2026-11-11"), path)
    _, info = module.load_home_ranking_with_fallback(snapshot_path=path)
    assert counter["count"] == 1
    assert info["source"] == "live"


def test_old_snapshot_without_fingerprint_is_not_reused(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    old = _info()
    old.pop("universe_fingerprint")
    old.pop("ranking_spec")
    module.save_ranking_snapshot(_frame(), old, path)
    _, info = module.load_home_ranking_with_fallback(snapshot_path=path)
    assert counter["count"] == 1
    assert info["source"] == "live"


def test_changed_universe_invalidates_snapshot(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    module.load_home_ranking_with_fallback(snapshot_path=path)
    monkeypatch.setattr(
        module, "get_sp500_tickers", lambda: pd.DataFrame({"ticker": ["BBB"]})
    )
    _, info = module.load_home_ranking_with_fallback(snapshot_path=path)
    assert counter["count"] == 2
    assert info["source"] == "live"


def test_changed_ranking_spec_invalidates_snapshot(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    old = _info()
    old["ranking_spec"] = "old-methodology"
    module.save_ranking_snapshot(_frame(), old, path)
    _, info = module.load_home_ranking_with_fallback(snapshot_path=path)
    assert counter["count"] == 1
    assert info["source"] == "live"


def test_force_refresh_fail_uses_snapshot_without_overwriting(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    module.load_home_ranking_with_fallback(snapshot_path=path)

    def fail(**kwargs):
        raise ConnectionError("falha de API")

    monkeypatch.setattr(module, "load_latest_multifactor_ranking", fail)
    saved, info = module.load_home_ranking_with_fallback(
        snapshot_path=path, force_refresh=True
    )
    assert saved.iloc[0]["score_preliminar"] == 1.0
    assert info["source"] == "snapshot"
    assert info["update_error_type"] == "ConnectionError"


def test_snapshot_return_count_can_expand_with_available_entries(monkeypatch, tmp_path):
    counter = {"count": 0}
    _setup(monkeypatch, counter)
    path = tmp_path / "ranking.json"
    module.load_home_ranking_with_fallback(snapshot_path=path)
    cached, info = module.load_home_ranking_with_fallback(max_top_n=10, snapshot_path=path)
    assert len(cached) == 1
    assert info["returned_count"] == 1
    assert counter["count"] == 1
