import numpy as np
import pandas as pd

def clean_ticker_list(tickers):
    """
    Retorna uma lista de tickers válidos, sem repetições.
    Aceita uma string individual ou coleções de primeiro nível,
    ignorando valores que não sejam strings.
    """
    if tickers is None:
      return []

    if isinstance(tickers, str):
      tickers = [tickers]

    clean_tickers = []
    seen_tickers = set()

    for item in tickers:
      if isinstance(item, str):
        candidates = [item]
      elif isinstance(item, (list, tuple, set)):
        candidates = item
      else:
        candidates = []

      for ticker in candidates:
        if (
          isinstance(ticker, str)
          and ticker not in seen_tickers
        ):
          clean_tickers.append(ticker)
          seen_tickers.add(ticker)

    return clean_tickers


def calculate_equal_weight_portfolio(prices, tickers):
    """
    Calcula uma carteira teórica com pesos iguais.
    """
    clean_tickers = clean_ticker_list(tickers)

    valid_tickers = [
      ticker
      for ticker in clean_tickers
      if ticker in prices.columns
    ]

    if not valid_tickers:
        return None

    selected_prices = prices[valid_tickers].dropna(how="all")

    if selected_prices.empty:
        return None

    returns = selected_prices.pct_change().dropna(how="all")
    portfolio_returns = returns.mean(axis=1)

    if portfolio_returns.empty:
        return None

    accumulated_returns = (1 + portfolio_returns).cumprod()

    initial_curve = pd.Series(
      [100.0],
      index=[selected_prices.index[0]],
    )

    portfolio_curve = pd.concat(
      [
        initial_curve,
        100 * accumulated_returns,
      ]
    )

    total_return = portfolio_curve.iloc[-1] / portfolio_curve.iloc[0] - 1

    days = (portfolio_curve.index[-1] - portfolio_curve.index[0]).days
    years = days / 365 if days > 0 else np.nan

    if years and years > 0:
        cagr = (portfolio_curve.iloc[-1] / portfolio_curve.iloc[0]) ** (1 / years) - 1
    else:
        cagr = np.nan

    volatility = portfolio_returns.std() * np.sqrt(252)

    if portfolio_returns.std() != 0:
        sharpe = portfolio_returns.mean() / portfolio_returns.std() * np.sqrt(252)
    else:
        sharpe = np.nan

    drawdown = portfolio_curve / portfolio_curve.cummax() - 1
    max_drawdown = drawdown.min()

    return {
        "curve": portfolio_curve,
        "returns": portfolio_returns,
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
    }

def calculate_evaluation_period_portfolio(
  prices,
  tickers,
  evaluation_start,
  evaluation_end=None,
):
  """
  Calcula a carteira Equal Weight somente durante
  o periodo de avaliação.
  Dados anterioress ao ínicio da avaliação são ignorados.
  """
  if not isinstance(prices.index, pd.DatetimeIndex):
    raise TypeError(
      "O índice de prices deve ser um DatetimeIndex."
    )

  evaluation_start = pd.Timestamp(evaluation_start)

  evaluation_prices = prices.loc[
    prices.index >= evaluation_start
  ].copy()

  if evaluation_end is not None:
    evaluation_end = pd.Timestamp(evaluation_end)

    if evaluation_end < evaluation_start:
      raise ValueError(
        "A data final da avaliação não pode ser "
        "anterior à data inicial."
      )

    evaluation_prices = evaluation_prices.loc[
      evaluation_prices.index <= evaluation_end
    ]

  if evaluation_prices.empty:
    raise ValueError(
      "Não existem preços disponíveis no periodo de avaliação."
    )

  return calculate_equal_weight_portfolio(
    prices=evaluation_prices,
    tickers=tickers,
  )

def build_portfolio_diagnosis(portfolio, metrics, benchmark="SPY"):
  """
  Compara uma carteira com o benchmark e gera um diagnóstico simples.
  """
  if portfolio is None:
    return (
      None,
      "Não foi possível calcular o diagnóstico da carteira.",
    )

  if (
    metrics.empty
    or benchmark not in metrics["Ticker"].values
  ):
    return (
      None,
      f"Benchmark {benchmark} não encontrado nas métricas.",
    )

  benchmark_metrics = metrics[
    metrics["Ticker"] == benchmark
  ].iloc[0]

  metric_definitions = [
    {
      "name": "CAGR",
      "portfolio_key": "cagr",
      "benchmark_column": "CAGR",
      "better_when": "Maior",
      "higher_is_better": True,
    },
    {
      "name": "Sharpe Ratio",
      "portfolio_key": "sharpe",
      "benchmark_column": "Sharpe",
      "better_when": "Maior",
      "higher_is_better": True,
    },
    {
      "name": "Volatilidade",
      "portfolio_key": "volatility",
      "benchmark_column": "Volatilidade",
      "better_when": "Menor",
      "higher_is_better": False,
    },
    {
      "name": "Max Drawdown",
      "portfolio_key": "max_drawdown",
      "benchmark_column": "Max Drawdown",
      "better_when": "Menos negativo",
      "higher_is_better": True,
    },
  ]

  diagnosis_data = []

  for definition in metric_definitions:
    portfolio_value = portfolio[
      definition["portfolio_key"]
    ]

    benchmark_value = benchmark_metrics[
      definition["benchmark_column"]
    ]

    if definition["higher_is_better"]:
      is_better = portfolio_value > benchmark_value
    else:
      is_better = portfolio_value < benchmark_value

    diagnosis_data.append(
      {
        "Métrica": definition["name"],
        "Carteira": portfolio_value,
        "Benchmark": benchmark_value,
        "Melhor quando": definition["better_when"],
        "Resultado": (
          "Melhor"
          if is_better
          else "Pior"
        ),
      }
    )

  diagnosis_df = pd.DataFrame(diagnosis_data)

  positive_results = (
    diagnosis_df["Resultado"] == "Melhor"
  ).sum()

  summaries = {
    4: (
      "A carteira superou o benchmark "
      "em todas as métricas principais."
    ),
    3: (
      "A carteira teve desempenho superior ao benchmark "
      "na maior parte das métricas."
    ),
    2: (
      "A carteira teve desempenho misto "
      "em relação ao benchmark."
    ),
    1: (
      "A carteira ficou abaixo do benchmark "
      "na maior parte das métricas."
    ),
    0: (
      "A carteira ficou pior que o benchmark "
      "em todas as métricas principais."
    ),
  }

  summary = summaries[positive_results]

  return diagnosis_df, summary