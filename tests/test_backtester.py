import numpy as np
import pandas as pd

from src.backtester import (
  calculate_returns_metrics,
  calculate_turnover,
  get_rebalance_dates,
  run_walk_forward_backtest,
)

def make_synthetic_market_data():
  dates = pd.bdate_range(
    start="2019-01-01",
    end="2021-12-31",
  )

  day_number = np.arange(len(dates))

  returns = pd.DataFrame(
    {
      "AAA": 0.0007 + 0.005 * np.sin(day_number / 17),
      "BBB": 0.0004 + 0.003 * np.cos(day_number / 23),
      "CCC": 0.0001 + 0.008 * np.sin(day_number / 11),
      "SPY": 0.0003 + 0.004 * np.sin(day_number / 19),
    },
    index=dates,
  )

  prices = 100 * (1 + returns).cumprod()

  volumes = pd.DataFrame(
    {
      "AAA": 1_000_000,
      "BBB": 800_000,
      "CCC": 600_000,
      "SPY": 5_000_000,
    },
    index=dates,
  )

  return prices, volumes

def test_get_rebalance_dates_monthly():
  prices, _ = make_synthetic_market_data()

  rebalance_dates = get_rebalance_dates(
    prices=prices,
    start_date="2020-01-01",
    end_date="2020-06-30",
    frequency="M",
  )

  assert len(rebalance_dates) == 6
  assert rebalance_dates[0].month == 1
  assert rebalance_dates[-1].month == 6

def test_get_rebalance_dates_quarterly():
  prices, _ = make_synthetic_market_data()

  rebalance_dates = get_rebalance_dates(
    prices=prices,
    start_date="2020-01-01",
    end_date="2020-12-31",
    frequency="Q",
  )

  assert len(rebalance_dates) == 4
  assert rebalance_dates[0].quarter == 1
  assert rebalance_dates[-1].quarter == 4

def test_calculate_turnover_first_portfolio():
  turnover = calculate_turnover(
    previous_tickers=[],
    current_tickers=["AAA", "BBB", "CCC"],
  )

  assert turnover == 1.0

def test_calculate_turnover_partial_change():
  turnover = calculate_turnover(
    previous_tickers=["AAA", "BBB", "CCC"],
    current_tickers=["AAA", "BBB", "SPY"],
  )

  assert turnover > 0
  assert turnover < 1

def test_calculate_returns_metrics():
  dates = pd.bdate_range(
    start="2021-01-01",
    periods=100,
  )

  returns = pd.Series(
    0.001,
    index=dates,
  )

  metrics = calculate_returns_metrics(returns)

  assert metrics is not None
  assert "curve" in metrics
  assert "total_return" in metrics
  assert "cagr" in metrics
  assert "volatility" in metrics
  assert "sharpe" in metrics
  assert "max_drawdown" in metrics
  assert metrics["total_return"] > 0

def test_run_walk_forward_backtest_returns_expected_outputs():
  prices, volumes = make_synthetic_market_data()

  result = run_walk_forward_backtest(
    prices=prices,
    volumes=volumes,
    start_date="2020-03-01",
    end_date="2021-12-31",
    top_n=2,
    benchmark="SPY",
    frequency="M",
    transaction_cost=0.001,
    slippage=0.001,
    momentum_weight=40,
    risk_weight=35,
    liquidity_weight=25,
  )

  assert "performance" in result
  assert "strategy_returns" in result
  assert "benchmark_returns" in result
  assert "strategy_metrics" in result
  assert "benchmark_metrics" in result
  assert "rebalance_log" in result

  assert not result["performance"].empty
  assert not result["rebalance_log"].empty

  assert "Estratégia Quant" in result["performance"].columns
  assert "SPY" in result["performance"].columns

def test_backtest_includes_final_holding_period():
  prices, volumes = make_synthetic_market_data()

  result = run_walk_forward_backtest(
    prices=prices,
    volumes=volumes,
    start_date="2020-03-01",
    end_date="2021-12-31",
    top_n=2,
    benchmark="SPY",
    frequency="M",
  )

  last_strategy_date = result["strategy_returns"].index.max()

  assert last_strategy_date.month == 12
  assert last_strategy_date.year == 2021

def test_transaction_costs_reduce_strategy_performance():
  prices, volumes = make_synthetic_market_data()

  without_costs = run_walk_forward_backtest(
    prices=prices,
    volumes=volumes,
    start_date="2020-03-01",
    end_date="2021-12-31",
    top_n=2,
    benchmark="SPY",
    frequency="M",
    transaction_cost=0.0,
    slippage=0.0,
  )

  with_costs = run_walk_forward_backtest(
    prices=prices,
    volumes=volumes,
    start_date="2020-03-01",
    end_date="2021-12-31",
    top_n=2,
    benchmark="SPY",
    frequency="M",
    transaction_cost=0.005,
    slippage=0.005,
  )

  assert (
    with_costs["strategy_metrics"]["total_return"]
    <
    without_costs["strategy_metrics"]["total_return"]
  )