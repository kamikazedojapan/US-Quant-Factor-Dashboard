"""
Funções para backtest walk-forward do modelo quantitativo.

A lógica principal é:
1. Definir datas de rebalanceamento.
2. Em cada data, calcular o ranking usando apenas dados anteriores.
3. Selecionar as Top N ações.
4. Segurar a carteira até o próximo rebalanceamento.
5. Aplicar custos e slippage com base no turnover.
6. Comparar a estratégia com o SPY.
"""

import numpy as np
import pandas as pd

from src.factors import calculate_out_of_sample_factor_scores


def get_rebalance_dates(prices, start_date, end_date, frequency="M"):
  """
  Gera datas reais de rebalanceamento com base nos pregões disponíveis.

  frequency:
  - "M": mensal
  - "Q": trimestral
  """

  if not isinstance(prices.index, pd.DatetimeIndex):
      raise TypeError("O índice de prices deve ser um DatetimeIndex.")

  start_date = pd.Timestamp(start_date)
  end_date = pd.Timestamp(end_date)

  available_dates = prices.loc[
      (prices.index >= start_date) & (prices.index <= end_date)
  ].index

  if available_dates.empty:
      return []

  if frequency == "M":
      grouped_dates = available_dates.to_series().groupby(
          available_dates.to_period("M")
      )
  elif frequency == "Q":
      grouped_dates = available_dates.to_series().groupby(
          available_dates.to_period("Q")
      )
  else:
      raise ValueError("frequency deve ser 'M' para mensal ou 'Q' para trimestral.")

  rebalance_dates = [
      group.iloc[0]
      for _, group in grouped_dates
  ]

  return rebalance_dates


def calculate_turnover(previous_tickers, current_tickers):
  """
  Calcula turnover simples com base na mudança dos ativos da carteira.

  Se não havia carteira anterior, considera turnover de 100%.
  """

  previous_set = set(previous_tickers)
  current_set = set(current_tickers)

  if not current_set:
      return 0.0

  if not previous_set:
      return 1.0

  removed_assets = previous_set - current_set
  added_assets = current_set - previous_set

  changed_assets = len(removed_assets) + len(added_assets)

  denominator = len(previous_set) + len(current_set)

  if denominator == 0:
      return 0.0

  turnover = changed_assets / denominator

  return turnover


def calculate_returns_metrics(returns):
  """
  Calcula métricas de performance a partir de uma série de retornos.
  """

  clean_returns = returns.replace(
      [np.inf, -np.inf],
      np.nan,
  ).dropna()

  if clean_returns.empty:
      return None

  curve = (1 + clean_returns).cumprod()
  curve = 100 * curve / curve.iloc[0]

  total_return = curve.iloc[-1] / curve.iloc[0] - 1

  days = (curve.index[-1] - curve.index[0]).days
  years = days / 365 if days > 0 else np.nan

  if years and years > 0:
      cagr = (curve.iloc[-1] / curve.iloc[0]) ** (1 / years) - 1
  else:
      cagr = np.nan

  volatility = clean_returns.std() * np.sqrt(252)

  if clean_returns.std() != 0:
      sharpe = clean_returns.mean() / clean_returns.std() * np.sqrt(252)
  else:
      sharpe = np.nan

  drawdown = curve / curve.cummax() - 1
  max_drawdown = drawdown.min()

  return {
      "curve": curve,
      "returns": clean_returns,
      "total_return": total_return,
      "cagr": cagr,
      "volatility": volatility,
      "sharpe": sharpe,
      "max_drawdown": max_drawdown,
  }


def run_walk_forward_backtest(
  prices,
  volumes,
  start_date,
  end_date,
  top_n=10,
  benchmark="SPY",
  frequency="M",
  transaction_cost=0.001,
  slippage=0.001,
  momentum_weight=40,
  risk_weight=35,
  liquidity_weight=25,
):
  """
  Executa um backtest walk-forward simples.

  Em cada data de rebalanceamento:
  - calcula o ranking usando dados anteriores à data;
  - seleciona as Top N ações;
  - monta uma carteira equal weight;
  - mantém a carteira até o próximo rebalanceamento.

  transaction_cost e slippage são aplicados de forma simplificada
  proporcionalmente ao turnover.
  """

  if benchmark not in prices.columns:
      raise ValueError(f"Benchmark {benchmark} não encontrado em prices.")

  start_date = pd.Timestamp(start_date)
  end_date = pd.Timestamp(end_date)

  rebalance_dates = get_rebalance_dates(
      prices=prices,
      start_date=start_date,
      end_date=end_date,
      frequency=frequency,
  )

  if len(rebalance_dates) < 2:
      raise ValueError(
          "Não há datas suficientes para executar o backtest. "
          "Tente aumentar o período de análise."
      )

  strategy_returns_parts = []
  rebalance_log = []

  previous_tickers = []

  for index, rebalance_date in enumerate(rebalance_dates):
      if index == len(rebalance_dates) - 1:
          break

      next_rebalance_date = rebalance_dates[index + 1]

      try:
          factor_scores = calculate_out_of_sample_factor_scores(
              prices=prices,
              volumes=volumes,
              evaluation_start=rebalance_date,
              benchmark=benchmark,
              momentum_weight=momentum_weight,
              risk_weight=risk_weight,
              liquidity_weight=liquidity_weight,
          )
      except ValueError:
          continue

      ranking_view = factor_scores.copy()

      if benchmark in ranking_view.index:
          ranking_view = ranking_view.drop(index=benchmark)

      ranking_view = ranking_view.dropna(subset=["score_preliminar"])

      if ranking_view.empty:
          continue

      selected_tickers = ranking_view.head(top_n).index.tolist()

      selected_tickers = [
          str(ticker)
          for ticker in selected_tickers
          if isinstance(ticker, str) and ticker in prices.columns
      ]

      if not selected_tickers:
          continue

      holding_prices = prices.loc[
          (prices.index >= rebalance_date)
          & (prices.index < next_rebalance_date),
          selected_tickers,
      ].copy()

      holding_prices = holding_prices.dropna(how="all")

      if len(holding_prices) < 2:
          continue

      holding_returns = holding_prices.pct_change().dropna(how="all")

      if holding_returns.empty:
          continue

      portfolio_returns = holding_returns.mean(axis=1)

      turnover = calculate_turnover(
          previous_tickers=previous_tickers,
          current_tickers=selected_tickers,
      )

      total_cost = turnover * (transaction_cost + slippage)

      if not portfolio_returns.empty:
          portfolio_returns.iloc[0] = portfolio_returns.iloc[0] - total_cost

      strategy_returns_parts.append(portfolio_returns)

      rebalance_log.append(
          {
              "rebalance_date": rebalance_date,
              "next_rebalance_date": next_rebalance_date,
              "selected_tickers": ", ".join(selected_tickers),
              "number_of_assets": len(selected_tickers),
              "turnover": turnover,
              "transaction_cost": transaction_cost,
              "slippage": slippage,
              "total_cost_applied": total_cost,
          }
      )

      previous_tickers = selected_tickers

  if not strategy_returns_parts:
      raise ValueError(
          "Não foi possível gerar retornos para o backtest. "
          "Verifique o período, os tickers selecionados e os dados disponíveis."
      )

  strategy_returns = pd.concat(strategy_returns_parts)
  strategy_returns = strategy_returns[~strategy_returns.index.duplicated(keep="first")]
  strategy_returns = strategy_returns.sort_index()

  benchmark_prices = prices.loc[
      strategy_returns.index,
      benchmark,
  ].dropna()

  benchmark_returns = benchmark_prices.pct_change().dropna()

  common_index = strategy_returns.index.intersection(benchmark_returns.index)

  strategy_returns = strategy_returns.loc[common_index]
  benchmark_returns = benchmark_returns.loc[common_index]

  strategy_metrics = calculate_returns_metrics(strategy_returns)
  benchmark_metrics = calculate_returns_metrics(benchmark_returns)

  if strategy_metrics is None:
      raise ValueError("Não foi possível calcular as métricas da estratégia.")

  if benchmark_metrics is None:
      raise ValueError("Não foi possível calcular as métricas do benchmark.")

  performance = pd.DataFrame(
      {
          "Estratégia Quant": strategy_metrics["curve"],
          benchmark: benchmark_metrics["curve"],
      }
  )

  rebalance_log_df = pd.DataFrame(rebalance_log)

  return {
      "performance": performance,
      "strategy_returns": strategy_returns,
      "benchmark_returns": benchmark_returns,
      "strategy_metrics": strategy_metrics,
      "benchmark_metrics": benchmark_metrics,
      "rebalance_log": rebalance_log_df,
  }