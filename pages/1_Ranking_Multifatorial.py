from datetime import datetime

import pandas as pd
import streamlit as st

from src.data_loader import download_market_data, get_sp500_tickers
from src.factors import calculate_price_volume_factor_scores
from src.portfolio import calculate_equal_weight_portfolio


st.set_page_config(
    page_title="Ranking Multifatorial",
    page_icon="📈",
    layout="wide",
)


st.title("Ranking Multifatorial")
st.caption(
    "Ranking quantitativo preliminar de ações americanas com base em momentum, "
    "baixo risco e liquidez."
)


sp500_df = get_sp500_tickers()

sp500_df["sector"] = sp500_df["sector"].fillna("Sem setor")
sp500_df["industry"] = sp500_df["industry"].fillna("Sem indústria")

sector_options = ["Todos"] + sorted(
    sp500_df["sector"].dropna().unique().tolist()
)


with st.sidebar:
    st.header("Configurações do Ranking")

    selected_sector = st.selectbox(
        "Filtrar por setor",
        options=sector_options,
        key="ranking_selected_sector",
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
        key=f"ranking_selected_tickers_{selected_sector}",
    )

    start_date = st.date_input(
        "Data inicial",
        value=datetime(2020, 1, 1),
        key="ranking_start_date",
    )

    end_date = st.date_input(
        "Data final",
        value=datetime.today(),
        key="ranking_end_date",
    )

    st.markdown("---")

    selected_count = len(selected_tickers)

    if selected_count == 0:
        top_n_quant = 1
        st.info("Selecione pelo menos uma ação para calcular o Top Ranking.")

    elif selected_count == 1:
        top_n_quant = 1
        st.info("Apenas uma ação selecionada. O Top Ranking será 1.")

    else:
        top_n_quant = st.slider(
            "Quantidade de ações no Top Ranking",
            min_value=1,
            max_value=selected_count,
            value=min(10, selected_count),
            key=f"ranking_top_n_quant_{selected_sector}_{selected_count}",
        )

    st.markdown("---")
    st.subheader("Pesos dos Fatores")

    momentum_weight = st.slider(
        "Peso Momentum",
        min_value=0,
        max_value=100,
        value=40,
        key="ranking_momentum_weight",
    )

    risk_weight = st.slider(
        "Peso Baixo Risco",
        min_value=0,
        max_value=100,
        value=35,
        key="ranking_risk_weight",
    )

    liquidity_weight = st.slider(
        "Peso Liquidez",
        min_value=0,
        max_value=100,
        value=25,
        key="ranking_liquidity_weight",
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


if prices.empty:
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


ranking_display = ranking_view.copy()
ranking_display.index.name = "ticker"
ranking_display = ranking_display.reset_index()

ranking_display = ranking_display.merge(
    sp500_df,
    on="ticker",
    how="left",
)

ranking_display.insert(
    0,
    "rank",
    range(1, len(ranking_display) + 1),
)


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

if quant_portfolio:
    st.subheader("Métricas da Carteira Quantitativa")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Retorno Total", f"{quant_portfolio['total_return']:.2%}")
    col2.metric("CAGR", f"{quant_portfolio['cagr']:.2%}")
    col3.metric("Volatilidade", f"{quant_portfolio['volatility']:.2%}")
    col4.metric("Max Drawdown", f"{quant_portfolio['max_drawdown']:.2%}")

    col5, col6 = st.columns(2)

    col5.metric("Sharpe Ratio", f"{quant_portfolio['sharpe']:.2f}")
    col6.metric("Ações no Top Ranking", len(top_quant_tickers))

col1, col2, col3, col4 = st.columns(4)

col1.metric("Ações analisadas", len(available_selected_tickers))
col2.metric("Top Ranking", top_n_quant)
col3.metric("Setor", selected_sector)
col4.metric("Benchmark", "SPY")


st.markdown("---")


st.subheader("Ranking Quantitativo Preliminar")

st.caption(
    "Este ranking usa apenas fatores calculados com preço e volume: "
    "momentum, baixo risco e liquidez."
)

ranking_columns = [
    "rank",
    "ticker",
    "company",
    "sector",
    "industry",
    "score_momentum",
    "score_risco",
    "score_liquidez",
    "score_preliminar",
    "retorno_3m",
    "retorno_6m",
    "retorno_12m",
    "retorno_12_1m",
    "volatilidade_252d",
    "beta",
    "max_drawdown_252d",
    "volume_medio_60d",
    "dollar_volume_60d",
]

available_ranking_columns = [
    column for column in ranking_columns if column in ranking_display.columns
]

st.dataframe(
    ranking_display[available_ranking_columns].style.format(
        {
            "score_momentum": "{:.2f}",
            "score_risco": "{:.2f}",
            "score_liquidez": "{:.2f}",
            "score_preliminar": "{:.2f}",
            "retorno_3m": "{:.2%}",
            "retorno_6m": "{:.2%}",
            "retorno_12m": "{:.2%}",
            "retorno_12_1m": "{:.2%}",
            "volatilidade_252d": "{:.2%}",
            "beta": "{:.2f}",
            "max_drawdown_252d": "{:.2%}",
            "volume_medio_60d": "{:,.0f}",
            "dollar_volume_60d": "${:,.0f}",
        }
    ),
    use_container_width=True,
)


st.markdown("---")


st.subheader(f"Carteira Quantitativa Top {top_n_quant}")

st.write("Ações selecionadas automaticamente pelo ranking quantitativo preliminar:")

portfolio_columns = [
    "rank",
    "ticker",
    "company",
    "sector",
    "industry",
    "score_momentum",
    "score_risco",
    "score_liquidez",
    "score_preliminar",
]

available_portfolio_columns = [
    column for column in portfolio_columns if column in ranking_display.columns
]

st.dataframe(
    ranking_display.head(top_n_quant)[available_portfolio_columns].style.format(
        {
            "score_momentum": "{:.2f}",
            "score_risco": "{:.2f}",
            "score_liquidez": "{:.2f}",
            "score_preliminar": "{:.2f}",
        }
    ),
    use_container_width=True,
)

st.markdown("---")

st.caption(
    "Aviso: este ranking é preliminar e utiliza apenas fatores baseados em preço e volume. "
    "Ele ainda não inclui fatores fundamentalistas como valor e qualidade. "
    "Este projeto é educacional e não representa recomendação de investimento."
)