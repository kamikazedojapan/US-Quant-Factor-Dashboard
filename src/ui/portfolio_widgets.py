"""Componentes visuais das carteiras e do diagnóstico."""

import streamlit as st

from src.portfolio import build_portfolio_diagnosis


def render_portfolio_summary(
  title,
  portfolio,
  count_label,
  count_value,
  empty_message,
):
  """
  Exibe as métricas principais de uma carteira.
  """

  st.subheader(title)

  if not portfolio:
    st.warning(
      empty_message
    )
    return

  col1, col2, col3, col4 = (
    st.columns(4)
  )

  col1.metric(
    "Retorno Total",
    f"{portfolio['total_return']:.2%}",
  )

  col2.metric(
    "CAGR",
    f"{portfolio['cagr']:.2%}",
  )

  col3.metric(
    "Volatilidade",
    f"{portfolio['volatility']:.2%}",
  )

  col4.metric(
    "Max Drawdown",
    f"{portfolio['max_drawdown']:.2%}",
  )

  col5, col6 = st.columns(2)

  col5.metric(
    "Sharpe Ratio",
    f"{portfolio['sharpe']:.2f}",
  )

  col6.metric(
    count_label,
    count_value,
  )


def render_quant_diagnosis(
  quant_portfolio,
  metrics,
):
  """
  Exibe o diagnóstico comparativo entre
  carteira quantitativa e SPY.
  """

  diagnosis_df, diagnosis_summary = (
    build_portfolio_diagnosis(
      portfolio=quant_portfolio,
      metrics=metrics,
      benchmark="SPY",
    )
  )

  if diagnosis_df is None:
    st.warning(
      diagnosis_summary
    )
    return

  st.info(
    diagnosis_summary
  )

  st.dataframe(
    diagnosis_df,
    use_container_width=True,
  )

  better_count = (
    diagnosis_df["Resultado"]
    == "Melhor"
  ).sum()

  if better_count >= 3:
    st.success(
      "A carteira quantitativa apresentou "
      "um resultado forte em relação ao SPY."
    )

  elif better_count == 2:
    st.warning(
      "A carteira quantitativa teve resultado "
      "equilibrado. Vale analisar o risco "
      "antes de decidir."
    )

  else:
    st.error(
      "A carteira quantitativa ficou fraca "
      "em relação ao SPY neste período."
    )
