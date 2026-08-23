import unittest
import pandas as pd

from src.portfolio import (
  build_portfolio_diagnosis,
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

class TestPortfolioDiagnosis(unittest.TestCase):
  @staticmethod
  def build_benchmark_metrics():
    return pd.DataFrame(
      [
        {
          "Ticker": "SPY",
          "CAGR": 0.10,
          "Sharpe": 1.00,
          "Volatilidade": 0.20,
          "Max Drawdown": -0.20,
        }
      ]
    )

  @staticmethod
  def build_portfolio_with_better_metrics(better_count):
    metric_values = [
      ("cagr", 0.20, 0.05),
      ("sharpe", 1.50, 0.50),
      ("volatility", 0.10, 0.30),
      ("max_drawdown", -0.10, -0.30),
    ]

    return {
      metric: better_value if index < better_count else worse_value
      for index, (
        metric,
        better_value,
        worse_value,
      ) in enumerate(metric_values)
    }

  def test_returns_error_when_portfolio_is_none(self):
    diagnosis, summary = build_portfolio_diagnosis(
      portfolio=None,
      metrics=self.build_benchmark_metrics(),
      benchmark="SPY",
    )

    self.assertIsNone(diagnosis)
    self.assertEqual(
      summary,
      "Não foi possível calcular o diagnóstico da carteira.",
    )

  def test_returns_error_when_metrics_are_empty(self):
    portfolio = self.build_portfolio_with_better_metrics(4)

    diagnosis, summary = build_portfolio_diagnosis(
      portfolio=portfolio,
      metrics=pd.DataFrame(),
      benchmark="SPY",
    )

    self.assertIsNone(diagnosis)
    self.assertEqual(
      summary,
      "Benchmark SPY não encontrado nas métricas.",
    )

  def test_returns_error_benchmark_is_missing(self):
    portfolio = self.build_portfolio_with_better_metrics(4)

    metrics = pd.DataFrame(
      [
        {
          "Ticker": "QQQ",
          "CAGR": 0.10,
          "Sharpe": 1.00,
          "Volatilidade": 0.20,
          "Max Drawdown": -0.20,
        }
      ]
    )

    diagnosis, summary = build_portfolio_diagnosis(
      portfolio=portfolio,
      metrics=metrics,
      benchmark="SPY",
    )

    self.assertIsNone(diagnosis)
    self.assertEqual(
      summary,
      "Benchmark SPY não encontrado nas métricas."
    )

  def test_compares_each_metric_in_the_correct_direction(self):
    portfolio = {
      "cagr": 0.15,
      "sharpe": 0.80,
      "volatility": 0.15,
      "max_drawdown": -0.10,
    }

    diagnosis, summary = build_portfolio_diagnosis(
      portfolio=portfolio,
      metrics=self.build_benchmark_metrics(),
      benchmark="SPY",
    )

    results = diagnosis.set_index("Métrica")["Resultado"].to_dict()

    self.assertEqual(
      results,
      {
        "CAGR": "Melhor",
        "Sharpe Ratio": "Pior",
        "Volatilidade": "Melhor",
        "Max Drawdown": "Melhor",
      },
    )

    self.assertEqual(
      summary,
      "A carteira teve desempenho superior ao benchmark "
      "na maior parte das métricas.",
    )

  def test_generates_summary_for_each_result_count(self):
    expected_summaries = {
      4: "A carteira superou o benchmark em todas as métricas principais.",
      3: (
        "A carteira teve desempenho superior ao benchmark "
        "na maior parte das métricas."
      ),
      2: "A carteira teve desempenho misto em relação ao benchmark.",
      1: "A carteira ficou abaixo do benchmark na maior parte das métricas.",
      0: "A carteira ficou pior que o benchmark em todas as métricas principais."
    }

    metrics = self.build_benchmark_metrics()

    for better_count, expected_summary in expected_summaries.items():
      with self.subTest(better_count=better_count):
        portfolio = self.build_portfolio_with_better_metrics(
          better_count
        )

        diagnosis, summary = build_portfolio_diagnosis(
          portfolio=portfolio,
          metrics=metrics,
          benchmark="SPY",
        )

        actual_better_count = (
          diagnosis["Resultado"] == "Melhor"
        ).sum()

        self.assertEqual(actual_better_count, better_count)
        self.assertEqual(summary, expected_summary)

  def test_equal_values_are_not_considered_better(self):
    portfolio = {
      "cagr": 0.10,
      "sharpe": 1.00,
      "volatility": 0.20,
      "max_drawdown": -0.20,
    }

    diagnosis, summary = build_portfolio_diagnosis(
      portfolio=portfolio,
      metrics=self.build_benchmark_metrics(),
      benchmark="SPY",
    )

    self.assertTrue(
      (diagnosis["Resultado"] == "Pior").all()
    )

    self.assertEqual(
      summary,
      "A carteira ficou pior que o benchmark "
      "em todas as métricas principais."
    )


if __name__ == "__main__":
  unittest.main()