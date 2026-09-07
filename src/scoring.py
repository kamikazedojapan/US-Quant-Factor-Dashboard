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

def normalize_factor_weights(weights, default_weights=None):
  """
  Normaliza os pesos dos fatores para que a soma seja 1.

  Exemplo:
  {
    "score_momentum": 40,
    "score_risco": 35,
    "score_liquidez": 25,
  }

  vira:

  {
    "score_momentum": 0.40,
    "score_risco": 0.35,
    "score_liquidez": 0.25,
  }
  """

  clean_weights = {}

  for factor_name, weight in weights.items():
    if pd.isna(weight):
      clean_weights[factor_name] = 0.0
    else:
      clean_weights[factor_name] = max(float(weight), 0.0)

  total_weight = sum(clean_weights.values())

  if total_weight == 0:
    if default_weights is None:
      default_weights = {
        factor_name: 1.0
        for factor_name in weights
      }

    return normalize_factor_weights(default_weights)

  normalized_weights = {
    factor_name: weight / total_weight
    for factor_name, weight in clean_weights.items()
  }

  return normalized_weights

def combine_weighted_scores(
  factors,
  score_weights,
  final_score_column="score_preliminar",
  default_weights = None,
):
  """
  Combina scores de fatores em uma pontuação final ponderada.

  A função ignora scores ausentes no cálculo da média ponderada.
  Isso evita que um fator NaN destrua o score final inteiro.
  """

  combined_factors = factors.copy()

  normalized_weights = normalize_factor_weights(
    weights=score_weights,
    default_weights=default_weights,
  )

  weighted_scores = pd.DataFrame(index=combined_factors.index)

  available_weights = pd.Series(
    0.0,
    index=combined_factors.index,
  )

  for column, weight in normalized_weights.items():
    if column not in combined_factors.columns:
      combined_factors[column] = np.nan

    valid_score = combined_factors[column].notna()

    weighted_scores[column] = combined_factors[column] * weight

    available_weights = available_weights + (
      valid_score.astype(float) * weight
    )

  score_sum = weighted_scores.sum(
    axis=1,
    skipna=True,
  )

  combined_factors[final_score_column] = np.where(
    available_weights > 0,
    score_sum / available_weights,
    np.nan,
  )

  combined_factors = combined_factors.dropna(
    subset=[final_score_column],
  )

  combined_factors = combined_factors.sort_values(
    final_score_column,
    ascending=False,
  )

  return combined_factors