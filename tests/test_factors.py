import unittest
import pandas as pd

from src.factors import (
  calculate_price_volume_factor_scores,
  calculate_risk_score,
  percentile_score,
)

class TestFactorRanking(unittest.TestCase):
  def test_benchmark_is_not_included_in_ranking(self):
    dates = pd.bdate_range(
      start="2023-01-02",
      periods=300,
    )

    prices = pd.DataFrame(
      {
        "AAA": [
          100 + (day * 0.20)
          for day in range(300)
        ],
        "BBB": [
          100 + (day * 0.10)
          for day in range(300)
        ],
        "SPY": [
          100 + (day * 0.15)
          for day in range(300)
        ],
      },
      index=dates,
    )

    volumes = pd.DataFrame(
      {
        "AAA": [8_000_000] * 300,
        "BBB": [4_000_000] * 300,
        "SPY": [15_000_000] * 300,
      },
      index=dates,
    )

    ranking = calculate_price_volume_factor_scores(
      prices=prices,
      volumes=volumes,
      benchmark="SPY"
    )

    self.assertNotIn(
      "SPY",
      ranking.index,
    )

  def test_percentile_score_uses_symmetric_scale(self):
    values = pd.Series(
      [10.0, 20.0, 30.0],
      index=["pior", "intermediario", "melhor"],
    )

    higher_scores = percentile_score(
      values,
      higher_is_better=True,
    )

    lower_scores = percentile_score(
      values,
      higher_is_better=False,
    )

    expected_higher_scores = [
      0.0,
      50.0,
      100.0,
    ]

    expected_lower_scores = [
      100.0,
      50.0,
      0.0,
    ]

    for actual, expected in zip(
      higher_scores,
      expected_higher_scores,
    ):
      self.assertAlmostEqual(
        actual,
        expected,
        places=10,
      )
    for actual, expected in zip(
      lower_scores,
      expected_lower_scores
    ):
      self.assertAlmostEqual(
        actual,
        expected,
        places=10,
      )

  def test_beta_uses_aligned_benchmark_period(self):
    dates = pd.date_range(
      start="2024-01-01",
      periods=6,
    )

    prices = pd.DataFrame(
      {
        "AAA": [
          None,
          None,
          100.0,
          110.0,
          99.0,
          118.8,
        ],
        "SPY": [
          100.0,
          101.0,
          103.0,
          104.0,
          108.0,
          109.0,
        ],
      },
      index=dates
    )

    risk = calculate_risk_score(
      prices=prices,
      benchmark="SPY",
    )

    returns = prices.pct_change().dropna(how="all")

    aligned_returns = pd.concat(
      [
        returns["AAA"].dropna(),
        returns["SPY"].dropna(),
      ],
      axis=1,
      join="inner",
    ).dropna()

    covariance = aligned_returns.iloc[:, 0].cov(
      aligned_returns.iloc[:, 1]
    )

    benchmark_variance = aligned_returns.iloc[:, 1].var()

    expected_beta = covariance / benchmark_variance

    self.assertAlmostEqual(
      risk.loc["AAA", "beta"],
      expected_beta,
      places=10,
    )

  def test_ranking_excludes_asset_without_twelve_month_history(self):
    dates = pd.bdate_range(
      start="2023-01-02",
      periods=300
    )

    full_prices = [
      100 + (day * 0.20)
      for day in range(300)
    ]

    short_prices = (
      [None] * 100
      + [
        50 + (day * 0.15)
        for day in range(200)
      ]
    )

    spy_prices = [
      100 + (day * 100)
      for day in range(300)
    ]

    prices = pd.DataFrame(
      {
        "FULL": full_prices,
        "SHORT": short_prices,
        "SPY": spy_prices,
      },
      index=dates
    )

    volumes = pd.DataFrame(
      {
        "FULL": [8_000_000] * 300,
        "SHORT": [5_000_000] * 300,
        "SPY": [15_000_000] * 300,
      },
      index=dates,
    )

    ranking = calculate_price_volume_factor_scores(
      prices=prices,
      volumes=volumes,
      benchmark="SPY",
    )

    self.assertIn(
      "FULL",
      ranking.index,
    )

    self.assertNotIn(
      "SHORT",
      ranking.index,
    )

  def test_ranking_requires_benchmark_data(self):
    dates = pd.bdate_range(
      start="2023-01-02",
      periods=300,
    )

    prices = pd.DataFrame(
      {
        "AAA": [
          100 + (day * 0.20)
          for day in range(300)
        ],
        "BBB": [
          100 + (day * 0.10)
          for day in range(300)
        ],
      },
      index=dates
    )

    volumes = pd.DataFrame(
      {
        "AAA": [8_000_000] * 300,
        "BBB": [5_000_000] * 300,
      },
      index=dates,
    )

    with self.assertRaisesRegex(
      ValueError,
      "Benchmark SPY"
    ):
      calculate_price_volume_factor_scores(
        prices=prices,
        volumes=volumes,
        benchmark="SPY",
      )

if __name__ == "__main__":
  unittest.main()