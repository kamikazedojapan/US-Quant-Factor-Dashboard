"""Teste estrutural: a Home não deve acionar a análise personalizada."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _calls(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def test_home_does_not_run_personalized_analysis():
    calls = _calls(ROOT / "Dashboard.py")
    assert "render_latest_ranking_section" in calls
    assert "render_personalized_analysis" not in calls
    assert "render_sidebar" not in calls
    assert "get_sp500_tickers" not in calls


def test_personalized_page_reuses_existing_analysis():
    calls = _calls(ROOT / "pages" / "2_Analise_Personalizada.py")
    assert "get_sp500_tickers" in calls
    assert "render_sidebar" in calls
    assert "render_personalized_analysis" in calls
