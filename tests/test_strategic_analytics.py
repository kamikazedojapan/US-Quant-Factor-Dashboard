"""Testes sintéticos e determinísticos, sem rede ou Streamlit."""

import numpy as np
import pandas as pd
import pytest

from src.strategic_analytics import (
    BENCHMARK,
    STRATEGY,
    align_returns,
    drawdown_series,
    growth_index,
    monthly_compounded_returns,
    rolling_volatility,
    summary_metrics,
)
from src.ui.strategic_charts import (
    drawdown_chart,
    monthly_heatmap,
    performance_chart,
    volatility_chart,
)


def sample(values_a, values_b, dates=None):
    if dates is None:
        dates = pd.bdate_range("2026-01-05", periods=len(values_a))
    return pd.DataFrame({STRATEGY: values_a, BENCHMARK: values_b}, index=dates)


def test_alignment_only_uses_common_valid_dates():
    a = pd.Series([0.02, 0.01, np.nan], index=pd.bdate_range("2026-01-05", periods=3))
    b = pd.Series([0.03, 0.04, 0.05], index=pd.bdate_range("2026-01-06", periods=3))
    # Overlap has only one valid date -> insufficient sample
    with pytest.raises(ValueError, match="pelo menos dois"):
        align_returns(a, b)
    a.iloc[-1] = 0.0
    aligned = align_returns(a, b)
    assert len(aligned) == 2
    assert aligned.index.min() == pd.Timestamp("2026-01-06")
    assert aligned.iloc[1][STRATEGY] == 0.0


def test_alignment_rejects_duplicate_dates_and_invalid_loss():
    dates = pd.to_datetime(["2026-01-05", "2026-01-05"])
    with pytest.raises(ValueError, match="duplicadas"):
        align_returns(pd.Series([0.1, 0.2], index=dates), pd.Series([0.1, 0.2], index=dates))
    dates = pd.bdate_range("2026-01-05", periods=2)
    with pytest.raises(ValueError, match="-100%"):
        align_returns(pd.Series([-1.1, 0.2], index=dates), pd.Series([0.0, 0.0], index=dates))


def test_growth_and_drawdown_include_initial_capital():
    returns = sample([-0.10, 0.20, -0.10], [0.00, 0.00, 0.00])
    values = growth_index(returns)
    assert values[STRATEGY].to_numpy() == pytest.approx([90, 108, 97.2])
    dd = drawdown_series(returns)
    assert dd[STRATEGY].to_numpy() == pytest.approx([-0.1, 0.0, -0.1])
    assert dd[BENCHMARK].eq(0).all()


def test_rolling_volatility_requires_full_window():
    returns = sample([0.01, -0.01, 0.02], [0.0, 0.0, 0.0])
    vol = rolling_volatility(returns, window=3)
    assert vol.iloc[:2].isna().all().all()
    assert vol.iloc[2][STRATEGY] == pytest.approx(np.std([0.01,-0.01,0.02], ddof=1) * np.sqrt(252))
    with pytest.raises(ValueError):
        rolling_volatility(returns, window=1)


def test_monthly_returns_compound_and_missing_month_stays_nan():
    dates = pd.to_datetime(["2026-01-30", "2026-03-02", "2026-03-03"])
    returns = sample([0.10, 0.10, -0.10], [0.0, 0.02, 0.0], dates)
    monthly = monthly_compounded_returns(returns)
    assert monthly.loc["2026-01-31", STRATEGY] == pytest.approx(0.10)
    assert np.isnan(monthly.loc["2026-02-28", STRATEGY])
    assert monthly.loc["2026-03-31", STRATEGY] == pytest.approx(-0.01)


def test_summary_metrics_constant_positive_daily_returns():
    returns = sample([0.001] * 252, [0.0] * 252)
    metrics = summary_metrics(returns)
    assert metrics.loc[STRATEGY, "Retorno total"] == pytest.approx((1.001)**252 - 1)
    assert metrics.loc[STRATEGY, "CAGR (252 pregões)"] == pytest.approx((1.001)**252 - 1)
    assert metrics.loc[STRATEGY, "Máximo drawdown"] == pytest.approx(0)
    assert np.isnan(metrics.loc[BENCHMARK, "Sharpe (rf=0)"])


def test_plotly_figures_build_from_synthetic_data():
    returns = sample([0.01, -0.005, 0.007] * 25, [0.003, 0.001, -0.002] * 25)
    for figure in (performance_chart(returns), drawdown_chart(returns), volatility_chart(returns)):
        assert len(figure.data) == 2
        assert figure.layout.paper_bgcolor == "#0B1220"
    heatmap = monthly_heatmap(returns, STRATEGY)
    assert heatmap.data[0].type == "heatmap"
    with pytest.raises(ValueError, match="Série não encontrada"):
        monthly_heatmap(returns, "INVALID")
