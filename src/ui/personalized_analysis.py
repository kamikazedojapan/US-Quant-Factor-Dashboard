"""Análise personalizada: dados, fatores, carteiras e gráficos."""

import pandas as pd
import streamlit as st

from src.data_loader import download_market_data
from src.factors import calculate_out_of_sample_factor_scores
from src.metrics import (
    build_risk_return_chart,
    calculate_asset_metrics,
    normalize_prices,
)
from src.portfolio import calculate_evaluation_period_portfolio
from src.ui.portfolio_widgets import (
    render_portfolio_summary,
    render_quant_diagnosis,
)


def render_personalized_analysis(config, sp500_df):
  """Executa o fluxo de análise com as configurações selecionadas."""

  # ----------------------------------------------------------
  # Validações iniciais
  # ----------------------------------------------------------

  selected_tickers = (
    config["selected_tickers"]
  )

  if not selected_tickers:
    st.info(
      "Selecione pelo menos uma ação "
      "na barra lateral."
    )
    return

  if not config[
    "weights_are_valid"
  ]:
    st.warning(
      "A análise personalizada requer "
      "pelo menos um peso de fator "
      "maior que zero."
    )
    return

  evaluation_start = pd.Timestamp(
    config["start_date"]
  )

  evaluation_end = pd.Timestamp(
    config["end_date"]
  )

  if (
    evaluation_end
    <= evaluation_start
  ):
    st.error(
      "A data final deve ser posterior "
      "à data inicial."
    )
    return

  # ----------------------------------------------------------
  # Download da análise personalizada
  # ----------------------------------------------------------

  download_tickers = (
    selected_tickers.copy()
  )

  if "SPY" not in download_tickers:
    download_tickers.append(
      "SPY"
    )

  formation_download_start = (
    evaluation_start
    - pd.DateOffset(
      months=18
    )
  )

  prices, volumes = (
    download_market_data(
      tickers=download_tickers,
      start_date=formation_download_start,
      end_date=config["end_date"],
    )
  )

  if prices.empty:
    st.error(
      "Não foi possível baixar os dados. "
      "Verifique os tickers ou o "
      "período escolhido."
    )
    return

  # ----------------------------------------------------------
  # Período de avaliação
  # ----------------------------------------------------------

  evaluation_prices = prices.loc[
    (
      prices.index
      >= evaluation_start
    )
    & (
      prices.index
      <= evaluation_end
    )
  ].copy()

  if evaluation_prices.empty:
    st.error(
      "Não existem dados disponíveis "
      "no período de avaliação."
    )
    return

  available_selected_tickers = [
    ticker
    for ticker in selected_tickers
    if ticker in prices.columns
  ]

  if "SPY" not in prices.columns:
    st.error(
      "Não foi possível obter os dados "
      "do SPY. O benchmark é necessário "
      "para calcular o fator de baixo risco."
    )
    return

  if not available_selected_tickers:
    st.error(
      "Nenhum dos tickers selecionados "
      "retornou dados válidos."
    )
    return

  # ----------------------------------------------------------
  # Métricas
  # ----------------------------------------------------------

  metrics = calculate_asset_metrics(
    evaluation_prices
  )

  normalized_prices = (
    normalize_prices(
      evaluation_prices
    )
  )

  # ----------------------------------------------------------
  # Carteira manual
  # ----------------------------------------------------------

  manual_portfolio = (
    calculate_evaluation_period_portfolio(
      prices=prices,
      tickers=available_selected_tickers,
      evaluation_start=evaluation_start,
      evaluation_end=evaluation_end,
    )
  )

  # ----------------------------------------------------------
  # Ranking OOS personalizado
  # ----------------------------------------------------------

  try:
    factor_scores = (
      calculate_out_of_sample_factor_scores(
        prices=prices,
        volumes=volumes,
        evaluation_start=evaluation_start,
        benchmark="SPY",
        momentum_weight=(
          config["momentum_weight"]
        ),
        risk_weight=(
          config["risk_weight"]
        ),
        liquidity_weight=(
          config["liquidity_weight"]
        ),
      )
    )

  except ValueError as error:
    st.error(
      str(error)
    )
    return

  ranking_view = (
    factor_scores.copy()
  )

  ranking_view = ranking_view.drop(
    index="SPY",
    errors="ignore",
  )

  ranking_view = ranking_view.dropna(
    subset=[
      "score_preliminar"
    ]
  )

  if ranking_view.empty:
    st.warning(
      "O ranking não gerou ações válidas "
      "para os filtros atuais. "
      "Tente aumentar o período de análise, "
      "reduzir a quantidade de ações "
      "ou verificar os dados baixados."
    )

    with st.expander(
      "Diagnóstico dos dados"
    ):
      st.write(
        "Tickers selecionados:",
        selected_tickers,
      )

      st.write(
        "Colunas de preços baixadas:",
        list(
          prices.columns
        ),
      )

      st.write(
        "Colunas de volume baixadas:",
        list(
          volumes.columns
        ),
      )

      st.dataframe(
        factor_scores
      )

    return

  top_n_quant = min(
    config["top_n_quant"],
    len(ranking_view),
  )

  top_quant_tickers = (
    ranking_view
    .head(top_n_quant)
    .index
    .tolist()
  )

  top_quant_tickers = [
    str(ticker)
    for ticker in top_quant_tickers
    if isinstance(
      ticker,
      str,
    )
  ]

  # ----------------------------------------------------------
  # Carteira quantitativa
  # ----------------------------------------------------------

  quant_portfolio = (
    calculate_evaluation_period_portfolio(
      prices=prices,
      tickers=top_quant_tickers,
      evaluation_start=evaluation_start,
      evaluation_end=evaluation_end,
    )
  )

  st.caption(
    f"Ranking formado com dados anteriores a "
    f"{evaluation_start.strftime('%d/%m/%Y')} "
    f"| Avaliação: "
    f"{evaluation_start.strftime('%d/%m/%Y')} "
    f"até "
    f"{evaluation_end.strftime('%d/%m/%Y')} "
    f"| Top {top_n_quant} ações"
  )

  # ----------------------------------------------------------
  # Resumo das carteiras
  # ----------------------------------------------------------

  render_portfolio_summary(
    title=(
      "Resumo da Carteira Manual "
      "Equal Weight"
    ),
    portfolio=manual_portfolio,
    count_label=(
      "Quantidade de Ações"
    ),
    count_value=len(
      available_selected_tickers
    ),
    empty_message=(
      "Não foi possível calcular "
      "a carteira manual com "
      "os dados disponíveis."
    ),
  )

  render_portfolio_summary(
    title=(
      "Resumo da Carteira Quantitativa"
    ),
    portfolio=quant_portfolio,
    count_label=(
      "Ações no Top Ranking"
    ),
    count_value=len(
      top_quant_tickers
    ),
    empty_message=(
      "Não foi possível calcular "
      "a carteira quantitativa."
    ),
  )

  # ----------------------------------------------------------
  # Diagnóstico
  # ----------------------------------------------------------

  render_quant_diagnosis(
    quant_portfolio=quant_portfolio,
    metrics=metrics,
  )

  # ----------------------------------------------------------
  # Desempenho relativo
  # ----------------------------------------------------------

  st.subheader(
    "Desempenho Relativo"
  )

  performance_df = pd.DataFrame(
    index=normalized_prices.index
  )

  if (
    config["show_spy"]
    and "SPY"
    in normalized_prices.columns
  ):
    performance_df["SPY"] = (
      normalized_prices["SPY"]
    )

  chart_mode = (
    config["chart_mode"]
  )

  if (
    chart_mode
    == (
      "Carteiras + todas as ações "
      "selecionadas"
    )
  ):
    assets_columns = [
      ticker
      for ticker
      in available_selected_tickers
      if (
        isinstance(
          ticker,
          str,
        )
        and ticker
        in normalized_prices.columns
      )
    ]

    if assets_columns:
      performance_df = (
        performance_df.join(
          normalized_prices[
            assets_columns
          ],
          how="left",
        )
      )

  elif (
    chart_mode
    == (
      "Carteiras + ações "
      "do Top Ranking"
    )
  ):
    top_assets_columns = [
      ticker
      for ticker
      in top_quant_tickers
      if (
        isinstance(
          ticker,
          str,
        )
        and ticker
        in normalized_prices.columns
      )
    ]

    if top_assets_columns:
      performance_df = (
        performance_df.join(
          normalized_prices[
            top_assets_columns
          ],
          how="left",
        )
      )

  if manual_portfolio:
    performance_df[
      "Carteira Manual Equal Weight"
    ] = manual_portfolio["curve"]

  if quant_portfolio:
    performance_df[
      f"Carteira Quant Top "
      f"{top_n_quant}"
    ] = quant_portfolio["curve"]

  if performance_df.empty:
    st.warning(
      "Nenhum dado disponível "
      "para exibir no gráfico."
    )

  else:
    st.line_chart(
      performance_df
    )

  # ----------------------------------------------------------
  # Métricas por ativo
  # ----------------------------------------------------------

  st.subheader(
    "Métricas por Ativo"
  )

  st.dataframe(
    metrics.style.format(
      {
        "Retorno Total": "{:.2%}",
        "CAGR": "{:.2%}",
        "Volatilidade": "{:.2%}",
        "Sharpe": "{:.2f}",
        "Max Drawdown": "{:.2%}",
      }
    ),
    use_container_width=True,
  )

  # ----------------------------------------------------------
  # Risco x Retorno
  # ----------------------------------------------------------

  st.subheader(
    "Risco x Retorno"
  )

  fig = build_risk_return_chart(
    metrics
  )

  st.plotly_chart(
    fig,
    use_container_width=True,
  )

  # ----------------------------------------------------------
  # Empresas selecionadas
  # ----------------------------------------------------------

  st.subheader(
    "Empresas Selecionadas"
  )

  selected_info = sp500_df[
    sp500_df["ticker"].isin(
      available_selected_tickers
    )
  ]

  st.dataframe(
    selected_info,
    use_container_width=True,
  )

  # ----------------------------------------------------------
  # Aviso
  # ----------------------------------------------------------

  st.markdown("---")

  st.caption(
    "Aviso: este projeto é educacional e não representa "
    "recomendação de investimento. "
    "A lista atual de ações pode gerar survivorship bias "
    "em análises históricas. "
    "O ranking atual é preliminar e ainda não inclui "
    "fatores fundamentalistas como valor e qualidade."
  )
