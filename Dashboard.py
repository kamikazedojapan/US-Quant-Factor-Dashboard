from datetime import datetime

import pandas as pd
import streamlit as st

from src.data_loader import download_market_data, get_sp500_tickers
from src.factors import calculate_price_volume_factor_scores
from src.metrics import (
  build_risk_return_chart,
  calculate_asset_metrics,
  normalize_prices,
)
from src.portfolio import (
  build_portfolio_diagnosis,
  calculate_equal_weight_portfolio,
)

st.set_page_config(
    page_title="US Quant Factor Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("US Quant Factor Dashboard")
st.caption(
    "Dashboard quantitativo para análise de ações americanas com foco em retorno, risco, liquidez e ranking multifatorial."
)

sp500_df = get_sp500_tickers()

sp500_df["sector"] = sp500_df["sector"].fillna("Sem setor")

sector_options = ["Todos"] + sorted(
  sp500_df["sector"].dropna().unique().tolist()
)

with st.sidebar:
    st.header("Configurações")

    selected_sector = st.selectbox(
        "Filtrar por setor",
        options=sector_options,
        key="selected_sector"
    )

    if selected_sector == "Todos":
        filtered_sp500_df = sp500_df.copy()
    else:
        filtered_sp500_df = sp500_df[sp500_df["sector"] == selected_sector].copy()

    tickers_list = filtered_sp500_df["ticker"].dropna().astype(str).tolist()

    default_tickers = [
        ticker
        for ticker in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
        if ticker in tickers_list
    ]

    if not default_tickers:
        default_tickers = tickers_list[:5]

    selected_tickers = st.multiselect(
        "Selecione as ações",
        options=tickers_list,
        default=default_tickers,
        key=f"selected_tickers_{selected_sector}",
    )

    start_date = st.date_input(
        "Data inicial",
        value=datetime(2020, 1, 1),
    )

    end_date = st.date_input(
        "Data final",
        value=datetime.today(),
    )

    show_spy = st.checkbox(
        "Exibir SPY no gráfico",
        value=True,
    )

    st.markdown("---")

    selected_count = len(selected_tickers)

    if selected_count == 0:
      top_n_quant = 1
      st.info("Selecione pelo menos uma ação para calcular o Top Ranking.")
    elif selected_count == 1:
      top_n_quant = 1
      st.info("Apenas uma ação disponível no setor. O top ranking será 1.")
    else:
      top_n_quant = st.slider(
        "Quantidade de ações no Top Ranking",
        min_value=1,
        max_value=selected_count,
        value=min(10, selected_count),
        key=f"top_n_quant_{selected_sector}_{selected_count}",
      )

    st.markdown("---")
    st.subheader("Pesos dos Fatores")

    momentum_weight = st.slider(
      "Peso Momentum",
      min_value=0,
      max_value=100,
      value=40,
    )

    risk_weight = st.slider(
      "Peso Baixo Risco",
      min_value=0,
      max_value=100,
      value=35,
    )

    liquidity_weight = st.slider(
      "Peso Liquidez",
      min_value=0,
      max_value=100,
      value=25,
    )

    total_weight = momentum_weight + risk_weight + liquidity_weight

    if total_weight == 0:
      st.warning("Defina pelo menos um peso maior do que zero.")
      st.stop()

    st.caption(
        f"Distribuição atual: "
        f"Momentum {momentum_weight / total_weight:.0%} | "
        f"Risco {risk_weight / total_weight:.0%} | "
        f"Liquidez {liquidity_weight / total_weight:.0%}"
    )

    st.markdown("---")
    st.subheader("Visualização")

    chart_mode = st.selectbox(
        "Modo gráfico",
        options=[
            "Apenas carteiras e SPY",
            "Carteiras + ações do Top Ranking",
            "Carteiras + todas as ações selecionadas",
        ],
    )


if not selected_tickers:
    st.info("Selecione pelo menos uma ação na barra lateral.")
    st.stop()

download_tickers = selected_tickers.copy()

if "SPY" not in download_tickers:
    download_tickers.append("SPY")


prices, volumes = download_market_data(
    tickers=download_tickers,
    start_date=start_date,
    end_date=end_date,
)


if "SPY" not in prices.columns:
  st.error(
    "Não foi possível obter os dados do SPY. "
    "O benchmark é necessário para calcular "
    "o fator de baixo risco."
  )
  st.stop()


available_selected_tickers = [
    ticker for ticker in selected_tickers if ticker in prices.columns
]


if not available_selected_tickers:
    st.error("Nenhum dos tickers selecionados retornou dados válidos.")
    st.stop()


metrics = calculate_asset_metrics(prices)
normalized_prices = normalize_prices(prices)

manual_portfolio = calculate_equal_weight_portfolio(
    prices=prices,
    tickers=available_selected_tickers,
)


factor_scores = calculate_price_volume_factor_scores(
    prices=prices,
    volumes=volumes,
    benchmark="SPY",
    momentum_weight=momentum_weight,
    risk_weight=risk_weight,
    liquidity_weight=liquidity_weight,
)


ranking_view = factor_scores.copy()

if "SPY" in ranking_view.index:
    ranking_view = ranking_view.drop(index="SPY")

top_n_quant = min(top_n_quant, len(ranking_view))

top_quant_tickers = ranking_view.head(top_n_quant).index.tolist()

top_quant_tickers = [
  str(ticker)
  for ticker in top_quant_tickers
  if isinstance(ticker, str)
]

quant_portfolio = calculate_equal_weight_portfolio(
    prices=prices,
    tickers=top_quant_tickers,
)


st.subheader("Resumo da Carteira Manual Equal Weight")

if manual_portfolio:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Retorno Total", f"{manual_portfolio['total_return']:.2%}")
    col2.metric("CAGR", f"{manual_portfolio['cagr']:.2%}")
    col3.metric("Volatilidade", f"{manual_portfolio['volatility']:.2%}")
    col4.metric("Max Drawdown", f"{manual_portfolio['max_drawdown']:.2%}")

    col5, col6 = st.columns(2)
    col5.metric("Sharpe Ratio", f"{manual_portfolio['sharpe']:.2f}")
    col6.metric("Quantidade de Ações", len(available_selected_tickers))
else:
    st.warning("Não foi possível calcular a carteira manual com os dados disponíveis.")

st.subheader("Diagnóstico da Carteira Quantitativa")

diagnosis_df, diagnosis_summary = build_portfolio_diagnosis(
  portfolio=quant_portfolio,
  metrics=metrics,
  benchmark="SPY",
)

if diagnosis_df is not None:
  st.info(diagnosis_summary)

  st.dataframe(
    diagnosis_df.style.format(
      {
        "Carteira": "{:.2f}",
        "Benchmark": "{:.2f}",
      }
    ),
    use_container_width=True,
  )

  better_count = (diagnosis_df["Resultado"] == "Melhor").sum()

  if better_count >= 3:
    st.success(
      "A carteira quantitativa apresentou um resultado forte em relação ao SPY."
    )
  elif better_count == 2:
    st.warning(
      "A carteira quantitativa teve resultado equilibrado. Vale analisar o risco antes de decidir."
    )
  else:
    st.error(
      "A carteira quantitativa ficou fraca em relação ao SPY neste periodo."
    )
else:
  st.warning(diagnosis_summary)

st.subheader("Desempenho Relativo")

performance_df = pd.DataFrame(index=normalized_prices.index)

if show_spy and "SPY" in normalized_prices.columns:
  performance_df["SPY"] = normalized_prices["SPY"]

if chart_mode == "Carteiras + todas as ações selecionadas":
  assets_columns = [
    ticker
    for ticker in available_selected_tickers
    if isinstance(ticker, str) and ticker in normalized_prices.columns
  ]

  if assets_columns:
    performance_df = performance_df.join(
      normalized_prices[assets_columns],
      how="left",
    )

elif chart_mode == "Carteiras + ações do Top Ranking":
  top_assets_columns = [
    ticker
    for ticker in top_quant_tickers
    if isinstance(ticker, str) and ticker in normalized_prices.columns
  ]

  if top_assets_columns:
    performance_df = performance_df.join(
      normalized_prices[top_assets_columns],
      how="left",
    )

if manual_portfolio:
  performance_df["Carteira Manual Equal Weight"] = manual_portfolio["curve"]

if quant_portfolio:
  performance_df[f"Carteira Quant Top {top_n_quant}"] = quant_portfolio["curve"]

if performance_df.empty:
  st.warning("Nenhum dado disponível para exibir no gráfico.")
else:
  st.line_chart(performance_df)

st.subheader("Métricas por Ativo")

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


st.subheader("Risco x Retorno")

fig = build_risk_return_chart(metrics)
st.plotly_chart(fig, use_container_width=True)


st.subheader("Empresas Selecionadas")

selected_info = sp500_df[sp500_df["ticker"].isin(available_selected_tickers)]

st.dataframe(
    selected_info,
    use_container_width=True,
)


st.markdown("---")

st.caption(
    "Aviso: este projeto é educacional e não representa recomendação de investimento. "
    "A lista atual de ações pode gerar survivorship bias em análises históricas. "
    "O ranking atual é preliminar e ainda não inclui fatores fundamentalistas como valor e qualidade."
)