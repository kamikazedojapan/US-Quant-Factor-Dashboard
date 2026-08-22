import unittest
import pandas as pd

from src.portfolio import (
  calculate_equal_weight_portfolio,
  calculate_evaluation_period_portfolio,
)

class TestEqualWeightPortfolio(unittest.TestCase):
  def test_total_return_includes_all_daily_returns(self):
    dates = pd.to_datetime(
      [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
      ]
    )

    prices = pd.DataFrame(
      {
        "AAA": [100.0, 110.0, 121.0],
        "BBB": [100.0, 110.0, 121.0],
      },
      index=dates
    )

    portfolio = calculate_equal_weight_portfolio(
      prices=prices,
      tickers=["AAA", "BBB"],
    )

    self.assertIsNotNone(portfolio)

    self.assertAlmostEqual(
      portfolio["total_return"],
      0.21,
      places=10,
    )

  def test_evaluation_portfolio_ignores_formation_period_returns(self):
    dates = pd.to_datetime(
      [
        "2024-12-30",
        "2024-12-31",
        "2025-01-02",
        "2025-01-03",
        "2025-01-06",
      ]
    )

    prices = pd.DataFrame(
      {
        "AAA": [50.0, 100.0, 100.0, 110.0, 121.0],
        "BBB": [50.0, 100.0, 100.0, 110.0, 121.0],
      },
      index=dates
    )

    evaluation_start = pd.Timestamp("2025-01-01")

    portfolio = calculate_evaluation_period_portfolio(
      prices=prices,
      tickers=["AAA", "BBB"],
      evaluation_start=evaluation_start,
    )

    self.assertIsNotNone(portfolio)

    # O retorno de 100% ocorrido durante a formação deve ser ignorado.
    self.assertAlmostEqual(
      portfolio["total_return"],
      0.21,
      places=10,
    )

    self.assertTrue(
      (
        portfolio["curve"].index
        >= evaluation_start
    ).all()
  )

if __name__ == "__main__":
  unittest.main()