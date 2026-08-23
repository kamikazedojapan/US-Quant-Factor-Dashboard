import unittest
import pandas as pd

from src.portfolio import (
  calculate_equal_weight_portfolio,
  calculate_evaluation_period_portfolio,
  clean_ticker_list,
)

class TestCleanTickerList(unittest.TestCase):
  def test_returns_empty_list_when_tickers_is_none(self):
    self.assertEqual(
      clean_ticker_list(None),
      [],
    )

  def test_accepts_single_ticker_string(self):
    self.assertEqual(
      clean_ticker_list("SPY"),
      ["SPY"],
    )

  def test_flattens_supported_collections_and_ignores_invalid_values(self):
    tickers = [
      "AAA",
      ["BBB", 123],
      ("CCC", None),
      {"DDD"},
      456,
    ]

    self.assertEqual(
      clean_ticker_list(tickers),
      ["AAA", "BBB", "CCC", "DDD"],
    )

  def test_removes_duplicates_preserving_original_order(self):
    tickers = [
      "AAA",
      ["BBB", "AAA"],
      ("CCC", "BBB"),
    ]

    self.assertEqual(
      clean_ticker_list(tickers),
      ["AAA", "BBB", "CCC"],
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

  def test_evaluation_porfolio_respects_end_date(self):
    dates = pd.to_datetime(
      [
        "2024-12-31",
        "2025-01-02",
        "2025-01-03",
        "2025-01-06",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [50.0, 100.0, 110.0, 121.0],
        "BBB": [50.0, 100.0, 110.0, 121.0],
      },
      index=dates
    )

    evaluation_start = pd.Timestamp("2025-01-01")
    evaluation_end = pd.Timestamp("2025-01-03")

    portfolio = calculate_evaluation_period_portfolio(
      prices=prices,
      tickers=["AAA", "BBB"],
      evaluation_start=evaluation_start,
      evaluation_end=evaluation_end,
    )

    self.assertIsNotNone(portfolio)
    self.assertAlmostEqual(
      portfolio["total_return"],
      0.10,
      places=10,
    )
    self.assertLessEqual(
      portfolio["curve"].index.max(),
      evaluation_end,
    )

  def test_evaluation_portfolio_rejects_end_before_start(self):
    dates = pd.to_datetime(
      [
        "2025-01-02",
        "2025-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 110.0],
      },
      index=dates,
    )

    with self.assertRaisesRegex(
      ValueError,
      "não pode ser anterior",
    ):
      calculate_evaluation_period_portfolio(
        prices=prices,
        tickers=["AAA"],
        evaluation_start="2025-01-03",
        evaluation_end="2025-01-02",
      )

  def test_evaluation_portfolio_rejects_non_datetime_index(self):
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 110.0],
      },
      index=[0, 1],
    )

    with self.assertRaisesRegex(
      TypeError,
      "DatetimeIndex",
    ):
      calculate_evaluation_period_portfolio(
        prices=prices,
        tickers=["AAA"],
        evaluation_start="2025-01-01",
      )

  def test_evaluation_portfolio_rejects_period_without_prices(self):
    dates = pd.to_datetime(
      [
        "2025-01-02",
        "2025-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 110.0],
      },
      index=dates,
    )

    with self.assertRaisesRegex(
      ValueError,
      "Não existem preços disponíveis",
    ):
      calculate_evaluation_period_portfolio(
        prices=prices,
        tickers=["AAA"],
        evaluation_start="2026-01-01",
      )

  def test_duplicate_tickers_do_not_change_portfolio_weights(self):
    dates = pd.to_datetime(
      [
        "2025-01-02",
        "2025-01-03",
      ]
    )
    prices = pd.DataFrame(
      {
        "AAA": [100.0, 110.0],
        "BBB": [100.0, 100.0],
      },
      index=dates
    )

    portfolio = calculate_equal_weight_portfolio(
      prices=prices,
      tickers=["AAA", "AAA", "BBB"],
    )

    self.assertIsNotNone(portfolio)
    self.assertAlmostEqual(
      portfolio["total_return"],
      0.05,
      places=10,
    )


if __name__ == "__main__":
  unittest.main()