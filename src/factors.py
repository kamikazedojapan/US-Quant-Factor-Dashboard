import numpy as np
import pandas as pd

def percentile_score(series, higher_is_better=True):
  """
  Converte uma série numérica em score de 0 a 100.

  O pior valor recebe 0.
  O melhor valor recebe 100.
  """
  clean_series = series.replace(
      [np.inf, -np.inf],
      np.nan,
  )

  valid_count = clean_series.notna().sum()

  if valid_count == 0:
      return pd.Series(
          np.nan,
          index=series.index,
          dtype=float,
      )

  if valid_count == 1:
      score = pd.Series(
          np.nan,
          index=series.index,
          dtype=float,
      )

      score.loc[clean_series.notna()] = 50.0

      return score

  ranks = clean_series.rank(
      method="average",
      ascending=True,
  )

  score = (
      (ranks - 1)
      / (valid_count - 1)
      * 100
  )

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

  asset_columns = [
    ticker
    for ticker in prices.columns
    if ticker != benchmark
  ]

  risk = pd.DataFrame(index=asset_columns)

  risk["volatilidade_252d"] = (
    returns[asset_columns].tail(252).std() * np.sqrt(252)
  )

  if benchmark in returns.columns:
    benchmark_returns = returns[benchmark].dropna()

    betas = {}

    for ticker in asset_columns:
      ticker_returns = returns[ticker].dropna()

      aligned_returns = pd.concat(
        [
          ticker_returns,
          benchmark_returns,
        ],
        axis=1,
        join="inner",
      ).dropna()

      if len(aligned_returns) < 2:
        betas[ticker] = np.nan
        continue

      aligned_benchmark_variance = (
        aligned_returns.iloc[:, 1].var()
      )

      if (
        pd.isna(aligned_benchmark_variance)
        or aligned_benchmark_variance == 0
      ):
        betas[ticker] = np.nan
        continue

      covariance = aligned_returns.iloc[:, 0].cov(
        aligned_returns.iloc[:, 1]
      )

      beta = covariance / aligned_benchmark_variance

      betas[ticker] = beta

    risk["beta"] = pd.Series(
      betas,
      dtype=float
    )
  else:
    risk["beta"] = np.nan

  drawdowns = {}

  for ticker in asset_columns:
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

def calculate_price_volume_factor_scores(
  prices,
  volumes,
  benchmark="SPY",
  momentum_weight=40,
  risk_weight=35,
  liquidity_weight=25,
):
  """
  Junta os fatores calculados com preço e volume:
  - Momentum
  - Baixo Risco
  - Liquidez
  """
  if benchmark not in prices.columns:
    raise ValueError(
      f"Benchmark {benchmark} não encontrado "
      "nos dados de preços."
    )

  ranking_prices = prices.drop(
    columns=[benchmark],
    errors="ignore",
  )

  minimum_history = 253

  eligible_tickers = [
    ticker
    for ticker in ranking_prices.columns
    if ranking_prices[ticker].dropna().shape[0]
    >= minimum_history
  ]

  ranking_prices = ranking_prices[
    eligible_tickers
  ]

  ranking_volumes = volumes.reindex(
    columns=eligible_tickers,
  )

  risk_columns = eligible_tickers.copy()

  if benchmark in prices.columns:
    risk_columns.append(benchmark)

  risk_prices = prices[
    risk_columns
  ]

  momentum = calculate_momentum_score(ranking_prices)

  risk = calculate_risk_score(
    risk_prices,
    benchmark=benchmark
  )

  liquidity = calculate_liquidity_score(
    ranking_prices,
    ranking_volumes,
  )

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

  total_weight = momentum_weight + risk_weight + liquidity_weight

  if total_weight == 0:
    momentum_weight = 40
    risk_weight = 35
    liquidity_weight = 25
    total_weight = 100

  momentum_weight = momentum_weight / total_weight
  risk_weight = risk_weight / total_weight
  liquidity_weight = liquidity_weight / total_weight

  factors["score_preliminar"] = (
      momentum_weight * factors["score_momentum"]
      + risk_weight * factors["score_risco"]
      + liquidity_weight * factors["score_liquidez"]
  )

  factors = factors.sort_values("score_preliminar", ascending=False)

  return factors

def calculate_out_of_sample_factor_scores(
  prices,
  volumes,
  evaluation_start,
  benchmark="SPY",
  momentum_weight=40,
  risk_weight=35,
  liquidity_weight=25,
):
  """
  Calcula o ranking usando somente os dados anteriores
  ao início do periodo de avaliação.

  Dados da data de avaliação em diante são ignorados.
  """
  if not isinstance(prices.index, pd.DatetimeIndex):
    raise TypeError(
      "O índice de prices deve ser um DatetimeIndex."
    )

  evaluation_start = pd.Timestamp(evaluation_start)

  formation_prices = prices.loc[
    prices.index < evaluation_start
  ].copy()

  formation_volumes = volumes.reindex(
    index=formation_prices.index,
    columns=formation_prices.columns,
  )

  if formation_prices.empty:
    raise ValueError(
      "Não existem dados anteriores ao periodo de avaliação.."
    )

  if benchmark not in formation_prices.columns:
    raise ValueError(
      f"O benchmark {benchmark} é obrigatório para calcular o ranking."
    )

  if formation_prices[benchmark].dropna().shape[0] < 253:
    raise ValueError(
      "O período de formação precisa ter pelo menos "
      "253 observações válidas ao benchmark."
    )

  return calculate_price_volume_factor_scores(
    prices=formation_prices,
    volumes=formation_volumes,
    benchmark=benchmark,
    momentum_weight=momentum_weight,
    risk_weight=risk_weight,
    liquidity_weight=liquidity_weight,
  )