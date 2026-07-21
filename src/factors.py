import numpy as np
import pandas as pd

def percentile_score(series, higher_is_better=True):
  """
  Converte uma série númerica em score percentil de 0 a 100.
  higher_is_better=True:
    valores maiores recebem score maior.

  higher_is_better=False:
    valores menores recebem score maior.
  """
  clean_series = series.replace([np.inf, -np.inf], np.nan)

  if clean_series.dropna().empty:
    return pd.Series(np.nan, index=series.index)

  score = clean_series.rank(pct=True) * 100

  if not higher_is_better:
    score = 100 - score

  return score

def calculate_momentum_score(prices):
  """
  Calcular o fator Momentum

  Métricas:
  - Retorno 3 meses
  - Retorno 6 meses
  - Retorno 12 meses
  - Retorno 12-1 meses
  """
  momentum = pd.DataFrame(index=prices.columns)

  momentum["retorno_3m"] = prices.pct_change(63).iloc[-1]
  momentum["retorno_6m"] = prices.pct_change(126).iloc[-1]
  momentum["retorno_12m"] = prices.pct_change(252).iloc[-1]

  price_1m_ago = prices.shift(21).iloc[-1]
  price_12m_ago = prices.shift(252).iloc[-1]

  momentum["retorno_12_1m"] = (price_1m_ago / price_12m_ago) - 1

  momentum["score_momentum"] = pd.concat(
    [
      percentile_score(momentum["retorno_3m"], higher_is_better=True),
      percentile_score(momentum["retorno_6m"], higher_is_better=True),
      percentile_score(momentum["retorno_12m"], higher_is_better=True),
      percentile_score(momentum["retorno_12_1m"], higher_is_better=True),
    ],
    axis=1,
  ).mean(axis=1)

  return momentum

def calculate_risk_score(prices, benchmark="SPY"):
  """
  Calcula o fator Baixo Risco.

  Métricas:
  - Volatilidade 252 dias
  - Beta contra benchmark
  - Max Drawdown 252 dias

  Quanto menor o risco, maior o score.
  """
  returns = prices.pct_change().dropna(how="all")

  risk = pd.DataFrame(index=prices.columns)

  risk["volatilidade_252d"] = returns.tail(252).std() * np.sqrt(252)

  if benchmark in returns.columns:
    benchmark_returns = returns[benchmark].dropna()
    benchmark_variance = benchmark_returns.var()

    betas = {}

    for ticker in returns.columns:
      ticker_returns = returns[ticker].dropna()

      aligned_returns = pd.concat(
        [ticker_returns, benchmark_returns],
        axis=1,
        join="inner",
      ).dropna()

      if aligned_returns.empty or benchmark_variance == 0:
        betas[ticker] = np.nan
      else:
        covariance = aligned_returns.iloc[:, 0].cov(aligned_returns.iloc[:, 1])
        beta = covariance / benchmark_variance
        betas[ticker] = beta

    risk["beta"] = pd.Series(betas)
  else:
    risk["beta"] = np.nan

  drawdowns = {}

  for ticker in prices.columns:
    series = prices[ticker].dropna().tail(252)

    if series.empty:
      drawdowns[ticker] = np.nan
      continue

    normalized = series / series.iloc[0]
    drawdown = normalized / normalized.cummax() - 1
    drawdowns[ticker] = drawdown.min()

  risk["max_drawdown_252d"] = pd.Series(drawdowns)

  risk["score_risco"] = pd.concat(
    [
      percentile_score(risk["volatilidade_252d"], higher_is_better=False),
      percentile_score(risk["beta"], higher_is_better=False),
      percentile_score(risk["max_drawdown_252d"], higher_is_better=True),
    ],
    axis=1,
  ).mean(axis=1)

  return risk

def calculate_liquidity_score(prices, volumes):
  """
  Calcula o fator Liquidez.

  Métricas:
  - Volume médio 60 dias
  - Dollar Volume médio 60 dias

  Dollar Volume = preço × volume
  """
  liquidity = pd.DataFrame(index=prices.columns)

  # Garante que volumes tenha as mesmas colunas de prices
  volumes = volumes.reindex(columns=prices.columns)

  avg_volume_60d = volumes.tail(60).mean()
  avg_dollar_volume_60d = (prices.tail(60) * volumes.tail(60)).mean()

  liquidity["volume_medio_60d"] = avg_volume_60d
  liquidity["dollar_volume_60d"] = avg_dollar_volume_60d

  liquidity["score_liquidez"] = pd.concat(
      [
          percentile_score(liquidity["volume_medio_60d"], higher_is_better=True),
          percentile_score(liquidity["dollar_volume_60d"], higher_is_better=True),
      ],
      axis=1,
  ).mean(axis=1)

  return liquidity

def calculate_price_volume_factor_scores(prices, volumes, benchmark="SPY"):
  """
  Junta os fatores calculados com preço e volume:
  - Momentum
  - Baixo Risco
  - Liquidez
  """
  momentum = calculate_momentum_score(prices)
  risk = calculate_risk_score(prices, benchmark=benchmark)
  liquidity = calculate_liquidity_score(prices, volumes)

  factors = momentum.join(risk, how="outer")
  factors = factors.join(liquidity, how="outer")

  required_columns = [
      "score_momentum",
      "score_risco",
      "score_liquidez",
  ]

  for column in required_columns:
      if column not in factors.columns:
          factors[column] = np.nan

  factors["score_preliminar"] = (
      0.40 * factors["score_momentum"]
      + 0.35 * factors["score_risco"]
      + 0.25 * factors["score_liquidez"]
  )

  factors = factors.sort_values("score_preliminar", ascending=False)

  return factors