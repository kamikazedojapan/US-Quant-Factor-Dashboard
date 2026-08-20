import unittest
import pandas as pd

from src.portfolio import calculate_equal_weight_portfolio

class TestEqualWeightPortifolio(unittest.TestCase):
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

if __name__ == "__main__":
  unittest.main()