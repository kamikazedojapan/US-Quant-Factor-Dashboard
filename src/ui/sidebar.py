"""Controles de configuração da análise personalizada."""

from datetime import datetime
import streamlit as st


def render_sidebar(sp500_df):
  """
  Renderiza as configurações utilizadas pela análise
  personalizada existente no dashboard.
  """

  sector_options = [
    "Todos",
    *sorted(
      sp500_df["sector"]
      .dropna()
      .unique()
      .tolist()
    ),
  ]

  with st.sidebar:
    st.header("Configurações")

    selected_sector = st.selectbox(
      "Filtrar por setor",
      options=sector_options,
      key="selected_sector",
    )

    if selected_sector == "Todos":
      filtered_sp500_df = sp500_df.copy()

    else:
      filtered_sp500_df = sp500_df[
        sp500_df["sector"]
        == selected_sector
      ].copy()

    tickers_list = (
      filtered_sp500_df["ticker"]
      .dropna()
      .astype(str)
      .tolist()
    )

    default_tickers = [
      ticker
      for ticker in [
        "AAPL",
        "MSFT",
        "NVDA",
        "AMZN",
        "GOOGL",
      ]
      if ticker in tickers_list
    ]

    if not default_tickers:
      default_tickers = tickers_list[:5]

    selected_tickers = st.multiselect(
      "Selecione as ações",
      options=tickers_list,
      default=default_tickers,
      key=(
        f"selected_tickers_"
        f"{selected_sector}"
      ),
    )

    start_date = st.date_input(
      "Data inicial da avaliação",
      value=datetime(2020, 1, 1),
    )

    end_date = st.date_input(
      "Data final da avaliação",
      value=datetime.today(),
    )

    st.caption(
      "O ranking Top N será formado usando dados "
      "anteriores à data inicial da avaliação."
    )

    show_spy = st.checkbox(
      "Exibir SPY no gráfico",
      value=True,
    )

    st.markdown("---")

    # --------------------------------------------------------
    # Top N da análise personalizada
    # --------------------------------------------------------

    selected_count = len(
      selected_tickers
    )

    if selected_count == 0:
      top_n_quant = 1

      st.info(
        "Selecione pelo menos uma ação "
        "para calcular o Top Ranking."
      )

    elif selected_count == 1:
      top_n_quant = 1

      st.info(
        "Apenas uma ação disponível no setor. "
        "O Top Ranking será 1."
      )

    else:
      top_n_quant = st.slider(
        "Quantidade de ações no Top Ranking",
        min_value=1,
        max_value=selected_count,
        value=min(
          10,
          selected_count,
        ),
        key=(
          f"top_n_quant_"
          f"{selected_sector}_"
          f"{selected_count}"
        ),
      )

    # --------------------------------------------------------
    # Pesos
    # --------------------------------------------------------

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

    total_weight = (
      momentum_weight
      + risk_weight
      + liquidity_weight
    )

    weights_are_valid = (
      total_weight > 0
    )

    if not weights_are_valid:
      st.warning(
        "Defina pelo menos um peso "
        "maior do que zero."
      )

    else:
      st.caption(
        f"Distribuição atual: "
        f"Momentum "
        f"{momentum_weight / total_weight:.0%} | "
        f"Risco "
        f"{risk_weight / total_weight:.0%} | "
        f"Liquidez "
        f"{liquidity_weight / total_weight:.0%}"
      )

    # --------------------------------------------------------
    # Visualização
    # --------------------------------------------------------

    st.markdown("---")
    st.subheader("Visualização")

    chart_mode = st.selectbox(
      "Modo gráfico",
      options=[
        "Apenas carteiras e SPY",
        "Carteiras + ações do Top Ranking",
        (
          "Carteiras + todas as ações "
          "selecionadas"
        ),
      ],
    )

  return {
    "selected_sector": selected_sector,
    "selected_tickers": selected_tickers,
    "start_date": start_date,
    "end_date": end_date,
    "show_spy": show_spy,
    "top_n_quant": top_n_quant,
    "momentum_weight": momentum_weight,
    "risk_weight": risk_weight,
    "liquidity_weight": liquidity_weight,
    "weights_are_valid": weights_are_valid,
    "chart_mode": chart_mode,
  }
