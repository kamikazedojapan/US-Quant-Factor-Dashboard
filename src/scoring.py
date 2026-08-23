"""
Funções genéricas para a pontuação e combinação de fatores.
"""

import numpy as np
import pandas as pd

def percentile_score(series, higher_is_better=True):
  """
  Converte uma série numérica em score de 0 a 100.

  O pior valor recebe 0.
  O melhor valor recebe 100.
  Valores iguais recebem o mesmo score.
  """
  clean_series = series.replace(
      [np.inf, -np.inf],
      np.nan,
  )

  if clean_series.notna().sum() == 0:
    return pd.Series(
      np.nan,
      index=series.index,
      dtype=float,
    )

  ranks = clean_series.rank(
    method="average",
    ascending=True
  )

  minimum_rank = ranks.min()
  maximum_rank = ranks.max()

  if minimum_rank == maximum_rank:
    scores = pd.Series(
      np.nan,
      index=series.index,
      dtype=float,
    )
    scores.loc[clean_series.notna()] = 50.0
    return scores

  scores = (
    (ranks - minimum_rank)
    / (maximum_rank - minimum_rank)
    * 100
  )

  if not higher_is_better:
    scores = 100 - scores

  return scores