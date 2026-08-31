from datetime import datetime

import pandas as pd
import streamlit as st

from src.data_loader import download_market_data, get_sp500_tickers
from src.metrics import calculate_asset_metrics, normalize_prices


st.set_page_config(
    page_title="Análise do Ativo",
    page_icon="🔎",
    layout="wide",
)


st.title("Análise do Ativo")
st.caption(
    "Página dedicada à análise individual de uma ação, com comparação contra o SPY, "
    "métricas de risco, retorno e drawdown."
)


sp500_df = get_sp500_tickers()
sp500_df["sector"] = sp500_df["sector"].fillna("Sem setor")

sector_options = ["Todos"] + sorted(
    sp500_df["sector"].dropna().unique().tolist()
)


with st.sidebar:
    st.header("Configurações da Análise")

    selected_sector = st.selectbox(
        "Filtrar por setor",
        options=sector_options,
        key="asset_selected_sector",
    )

    if selected_sector == "Todos":
        filtered_sp500_df = sp500_df.copy()
    else:
        filtered_sp500_df = sp500_df[
            sp500_df["sector"] == selected_sector
        ].copy()

    tickers_list = filtered_sp500_df["ticker"].dropna().astype(str).tolist()

    if not tickers_list:
        st.warning("Nenhuma ação encontrada para o setor selecionado.")
        st.stop()

    selected_ticker = st.selectbox(
        "Selecione uma ação",
        options=tickers_list,
        key=f"asset_selected_ticker_{selected_sector}",
    )

    start_date = st.date_input(
        "Data inicial",
        value=datetime(2020, 1, 1),
        key="asset_start_date",
    )

    end_date = st.date_input(
        "Data final",
        value=datetime.today(),
        key="asset_end_date",
    )

    show_spy = st.checkbox(
        "Comparar com SPY",
        value=True,
        key="asset_show_spy",
    )


analysis_start = pd.Timestamp(start_date)
analysis_end = pd.Timestamp(end_date)

if analysis_end <= analysis_start:
    st.error("A data final deve ser posterior à data inicial.")
    st.stop()


download_tickers = [selected_ticker]

if show_spy and selected_ticker != "SPY":
    download_tickers.append("SPY")


prices, volumes = download_market_data(
    tickers=download_tickers,
    start_date=analysis_start,
    end_date=analysis_end,
)


if prices.empty:
    st.error(
        "Não foi possível baixar os dados. "
        "Verifique o ticker ou o período escolhido."
    )
    st.stop()


if selected_ticker not in prices.columns:
    st.error("O ativo selecionado não retornou dados válidos.")
    st.stop()


selected_ticker_prices = prices[selected_ticker].dropna()

if len(selected_ticker_prices) < 2:
  st.warning(
    "Não existem dados suficientes para calcular as metricas do ativo selecionados. "
    "Tente escolher um período maior."
  )

  with st.expander("Diagnóstico dos dados"):
    st.write("Ticker selecionado:", selected_ticker)
    st.write("Tickers baixados:", list(prices.columns))
    st.write("Quantidade de preços válidos:", len(selected_ticker_prices))

  st.stop()

metrics = calculate_asset_metrics(prices)
normalized_prices = normalize_prices(prices)


if metrics.empty or "Ticker" not in metrics.columns:
  st.warning(
    "Não foi possível calcular as métricas para os dados baixados. "
    "Tente aumentar o período da análise."
  )

  with st.expander("Diagnóstico dos dados"):
    st.write("Ticker selecionado:", selected_ticker)
    st.write("Tickers baixados:", list(prices.columns))
    st.write("Formato da tabela de preços", prices.shape)
    st.dataframe(prices.tail())

  st.stop()

ticker_metrics = metrics[metrics["Ticker"] == selected_ticker]

if ticker_metrics.empty:
  st.error("Não foi possível calcular as métricas do ativo selecionado.")
  st.stop()

ticker_metrics = ticker_metrics.iloc[0]

company_info = sp500_df[sp500_df["ticker"] == selected_ticker]


st.subheader("Resumo do Ativo")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Ticker", selected_ticker)

if not company_info.empty:
    col2.metric("Empresa", company_info.iloc[0]["company"])
    col3.metric("Setor", company_info.iloc[0]["sector"])
    col4.metric("Indústria", company_info.iloc[0]["industry"])
else:
    col2.metric("Empresa", "Não encontrada")
    col3.metric("Setor", "Não encontrado")
    col4.metric("Indústria", "Não encontrada")


st.markdown("---")

st.subheader("Métricas Principais")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Retorno Total", f"{ticker_metrics['Retorno Total']:.2%}")
col2.metric("CAGR", f"{ticker_metrics['CAGR']:.2%}")
col3.metric("Volatilidade", f"{ticker_metrics['Volatilidade']:.2%}")
col4.metric("Max Drawdown", f"{ticker_metrics['Max Drawdown']:.2%}")

col5, col6 = st.columns(2)

col5.metric("Sharpe Ratio", f"{ticker_metrics['Sharpe']:.2f}")

if show_spy and "SPY" in metrics["Ticker"].values:
    spy_metrics = metrics[metrics["Ticker"] == "SPY"].iloc[0]
    difference_vs_spy = ticker_metrics["CAGR"] - spy_metrics["CAGR"]
    col6.metric("Diferença CAGR vs SPY", f"{difference_vs_spy:.2%}")
else:
    col6.metric("Benchmark", "SPY não utilizado")


st.markdown("---")

st.subheader("Desempenho Normalizado")

performance_df = pd.DataFrame(index=normalized_prices.index)

if selected_ticker in normalized_prices.columns:
    performance_df[selected_ticker] = normalized_prices[selected_ticker]

if show_spy and "SPY" in normalized_prices.columns:
    performance_df["SPY"] = normalized_prices["SPY"]

if performance_df.empty:
    st.warning("Nenhum dado disponível para exibir no gráfico.")
else:
    st.line_chart(performance_df)


st.markdown("---")

st.subheader("Drawdown do Ativo")

ticker_prices = prices[selected_ticker].dropna()

if ticker_prices.empty:
    st.warning("Não foi possível calcular o drawdown do ativo.")
else:
    normalized_ticker = ticker_prices / ticker_prices.iloc[0]
    drawdown = normalized_ticker / normalized_ticker.cummax() - 1

    drawdown_df = pd.DataFrame(
        {
            "Drawdown": drawdown,
        }
    )

    st.line_chart(drawdown_df)


st.markdown("---")

st.subheader("Tabela de Métricas")

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


st.markdown("---")

st.subheader("Dados da Empresa")

if company_info.empty:
    st.warning("Não foram encontradas informações cadastrais para este ticker.")
else:
    st.dataframe(
        company_info,
        use_container_width=True,
    )


st.markdown("---")

st.caption(
    "Aviso: esta análise é educacional e não representa recomendação de investimento. "
    "As métricas apresentadas dependem do período selecionado e da qualidade dos dados disponíveis."
)