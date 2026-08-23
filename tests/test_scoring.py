import unittest

import numpy as np
import pandas as pd

from src.factors import percentile_score

class TestPercentileScore(unittest.TestCase):
  def test_returns_nan_when_all_values_are_invalid(self):
    values = pd.Series(
      [np.nan, np.inf, -np.inf],
      index=["AAA", "BBB", "CCC"],
    )

    scores = percentile_score(values)

    self.assertTrue(scores.isna().all())

  def test_single_valid_value_receives_neutral_score(self):
    values = pd.Series(
      [np.nan, 25.0, np.nan],
      index=["AAA", "BBB", "CCC"],
    )

    scores = percentile_score(values)

    self.assertTrue(np.isnan(scores.loc["AAA"]))
    self.assertEqual(scores.loc["BBB"], 50.0)
    self.assertTrue(np.isnan(scores.loc["CCC"]))

  def test_tied_extreme_values_reach_zero_and_one_hundred(self):
    values = pd.Series(
      [10.0, 10.0, 20.0, 30.0, 30.0],
      index=["A", "B", "C", "D", "E"],
    )

    scores = percentile_score(values)

    expected = pd.Series(
      [0.0, 0.0, 50.0, 100.0, 100.0],
      index=values.index,
    )

    pd.testing.assert_series_equal(
      scores,
      expected,
    )

  def test_infinite_values_are_excluded_from_scoring(self):
    values = pd.Series(
      [10.0, np.inf, -np.inf, 20.0],
      index=["A", "B", "C", "D"],
    )

    scores = percentile_score(values)

    expected = pd.Series(
      [0.0, np.nan, np.nan, 100.0],
      index=values.index,
    )

    pd.testing.assert_series_equal(
      scores,
      expected,
    )


if __name__ == "__main__":
  unittest.main()