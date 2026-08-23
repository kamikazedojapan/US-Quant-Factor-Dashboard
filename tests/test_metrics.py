import unittest

import numpy as np
import pandas as pd

from src.metrics import (
  build_risk_return_chart,
  calculate_asset_metrics,
  normalize_prices,
)

class TestCalculateAssetMetrics(unittest.TestCase):
  def test_calculates_return_volatility_sharpe_and_drawdown(self):
    dates = pd.to_datetime(
      [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 110.0, 99.0],
      },
      index=dates,
    )

    metrics = calculate_asset_metrics(prices)
    asset_metrics = metrics.set_index("Ticker").loc["AAA"]

    expected_returns = pd.Series([0.10, -0.10])
    expected_volatility = (
      expected_returns.std() * np.sqrt(252)
    )

    self.assertAlmostEqual(
      asset_metrics["Retorno Total"],
      -0.01,
      places=10
    )
    self.assertAlmostEqual(
      asset_metrics["Volatilidade"],
      expected_volatility,
      places=10,
    )
    self.assertAlmostEqual(
      asset_metrics["Sharpe"],
      0.0,
      places=10,
    )
    self.assertAlmostEqual(
      asset_metrics["Max Drawdown"],
      -0.10,
      places=10,
    )

  def test_calculates_cagr_for_one_year_period(self):
    dates = pd.to_datetime(
      [
        "2024-01-01",
        "2024-12-31",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 121.0],
      },
      index=dates
    )

    metrics = calculate_asset_metrics(prices)
    asset_metrics = metrics.iloc[0]

    self.assertAlmostEqual(
      asset_metrics["CAGR"],
      0.21,
      places=10,
    )

  def test_skips_asset_without_two_valid_prices(self):
    dates = pd.to_datetime(
      [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "SHORT": [100.0, np.nan, np.nan],
        "FULL": [100.0, 110.0, 121.0],
      },
      index=dates,
    )

    metrics = calculate_asset_metrics(prices)

    self.assertEqual(
      metrics["Ticker"].tolist(),
      ["FULL"],
    )

  def test_constant_prices_produce_zero_volatility_and_nan_sharpe(self):
    dates = pd.to_datetime(
      [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 100.0, 100.0],
      },
      index=dates,
    )

    metrics = calculate_asset_metrics(prices)
    asset_metrics = metrics = metrics.iloc[0]

    self.assertAlmostEqual(
      asset_metrics["Volatilidade"],
      0.0,
      places=10,
    )
    self.assertTrue(
      np.isnan(asset_metrics["Sharpe"])
    )
    self.assertAlmostEqual(
      asset_metrics["Max Drawdown"],
      0.0,
      places=10,
    )


class TestNormalizePrices(unittest.TestCase):
  def test_normalizes_each_asset_from_first_valid_price(self):
    dates = pd.to_datetime(
      [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [np.nan, 50.0, 75.0],
        "BBB": [200.0, 100.0, 50.0],
      },
      index=dates,
    )

    normalized = normalize_prices(prices)

    expected = pd.DataFrame(
      {
        "AAA": [np.nan, 100.0, 150.0],
        "BBB": [100.0, 50.0, 25.0],
      },
      index=dates,
    )

    pd.testing.assert_frame_equal(
      normalized,
      expected,
    )


class TestBuildRiskReturnChart(unittest.TestCase):
  def test_builds_chart_with_expected_configuration(self):
    metrics = pd.DataFrame(
      {
        "Ticker": ["AAA", "BBB"],
        "Volatilidade": [0.20, 0.30],
        "CAGR": [0.15, 0.25],
        "Sharpe": [0.75, 0.83],
      }
    )

    figure = build_risk_return_chart(metrics)

    self.assertEqual(
      figure.layout.title.text,
      "Risco x Retorno",
    )
    self.assertEqual(
      figure.layout.xaxis.tickformat,
      ".0%",
    )
    self.assertEqual(
      figure.layout.xaxis.tickformat,
      ".0%",
    )
    self.assertEqual(
      figure.layout.height,
      600,
    )
    self.assertEqual(
      figure.data[0].marker.size,
      24,
    )


if __name__ == "__main__":
  unittest.main()