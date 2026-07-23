from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

from src.factors import calculate_price_volume_factor_scores


st.set_page_config(
    page_title="US Quant Factor Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def get_sp500_tickers():
    """
    Carrega uma lista local de ações americanas.

    O arquivo deve estar em:
    data/tickers_sp500.csv
    """
    try:
        tickers_df = pd.read_csv("data/tickers_sp500.csv")
        return tickers_df

    except FileNotFoundError:
        st.error(
            "Arquivo data/tickers_sp500.csv não encontrado. "
            "Crie o arquivo antes de executar o dashboard."
        )
        st.stop()


@st.cache_data(show_spinner=True)
def download_market_data(tickers, start_date, end_date):
    """
    Baixa preços ajustados e volume dos tickers selecionados usando yfinance.
    """
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()

    data = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        auto_adjust=True,
        progress=False,
        group_by="column",
    )

    if data.empty:
        return pd.DataFrame(), pd.DataFrame()

    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"].copy()
        volumes = data["Volume"].copy()
    else:
        ticker = tickers[0]

        prices = data[["Close"]].copy()
        prices.columns = [ticker]

        volumes = data[["Volume"]].copy()
        volumes.columns = [ticker]

    prices = prices.sort_index().dropna(how="all")
    volumes = volumes.sort_index().dropna(how="all")

    return prices, volumes


def calculate_asset_metrics(prices):
    """
    Calcula métricas individuais para cada ativo.
    """
    metrics = []

    for ticker in prices.columns:
        series = prices[ticker].dropna()

        if len(series) < 2:
            continue

        returns = series.pct_change().dropna()

        if returns.empty:
            continue

        first_price = series.iloc[0]
        last_price = series.iloc[-1]

        total_return = (last_price / first_price) - 1

        days = (series.index[-1] - series.index[0]).days
        years = days / 365 if days > 0 else np.nan

        if years and years > 0:
            cagr = (last_price / first_price) ** (1 / years) - 1
        else:
            cagr = np.nan

        volatility = returns.std() * np.sqrt(252)

        if returns.std() != 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        else:
            sharpe = np.nan

        normalized = series / first_price
        drawdown = normalized / normalized.cummax() - 1
        max_drawdown = drawdown.min()

        metrics.append(
            {
                "Ticker": ticker,
                "Retorno Total": total_return,
                "CAGR": cagr,
                "Volatilidade": volatility,
                "Sharpe": sharpe,
                "Max Drawdown": max_drawdown,
            }
        )

    return pd.DataFrame(metrics)


def normalize_prices(prices):
    """
    Normaliza os preços para base 100.
    """
    normalized = pd.DataFrame(index=prices.index)

    for ticker in prices.columns:
        series = prices[ticker].dropna()

        if series.empty:
            continue

        normalized[ticker] = 100 * prices[ticker] / series.iloc[0]

    return normalized


def calculate_equal_weight_portfolio(prices, tickers):
    """
    Calcula uma carteira teórica com pesos iguais.
    """
    valid_tickers = [ticker for ticker in tickers if ticker in prices.columns]

    if not valid_tickers:
        return None

    selected_prices = prices[valid_tickers].dropna(how="all")

    if selected_prices.empty:
        return None

    returns = selected_prices.pct_change().dropna(how="all")
    portfolio_returns = returns.mean(axis=1)

    if portfolio_returns.empty:
        return None

    portfolio_curve = (1 + portfolio_returns).cumprod()
    portfolio_curve = 100 * portfolio_curve / portfolio_curve.iloc[0]

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


def build_risk_return_chart(metrics):
    """
    Cria gráfico de risco x retorno.
    """
    fig = px.scatter(
        metrics,
        x="Volatilidade",
        y="CAGR",
        text="Ticker",
        color="Sharpe",
        title="Risco x Retorno",
    )

    fig.update_traces(
        marker=dict(size=24),
        textposition="top center",
    )

    fig.update_layout(
        xaxis_tickformat=".0%",
        yaxis_tickformat=".0%",
        height=600,
    )

    return fig


st.title("US Quant Factor Dashboard")
st.caption(
    "Dashboard quantitativo para análise de ações americanas com foco em retorno, risco, liquidez e ranking multifatorial."
)

sp500_df = get_sp500_tickers()
tickers_list = sp500_df["ticker"].tolist()

with st.sidebar:
    st.header("Configurações")

    selected_tickers = st.multiselect(
        "Selecione as ações",
        options=tickers_list,
        default=["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"],
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
        "Adicionar SPY como benchmark",
        value=True,
    )

    st.markdown("---")

    max_top_n = max(1, len(selected_tickers))

    top_n_quant = st.slider(
        "Quantidade de ações no Top Ranking",
        min_value=1,
        max_value=max_top_n,
        value=min(10, max_top_n),
    )


if not selected_tickers:
    st.info("Selecione pelo menos uma ação na barra lateral.")
    st.stop()


download_tickers = selected_tickers.copy()

if show_spy and "SPY" not in download_tickers:
    download_tickers.append("SPY")


prices, volumes = download_market_data(
    tickers=download_tickers,
    start_date=start_date,
    end_date=end_date,
)


if prices.empty:
    st.error("Não foi possível baixar os dados. Verifique os tickers ou o período escolhido.")
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
)


ranking_view = factor_scores.copy()

if "SPY" in ranking_view.index:
    ranking_view = ranking_view.drop(index="SPY")

top_n_quant = min(top_n_quant, len(ranking_view))

top_quant_tickers = ranking_view.head(top_n_quant).index.tolist()

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


st.subheader("Ranking Quantitativo Preliminar")

st.caption(
    "Este ranking usa apenas fatores calculados com preço e volume: momentum, baixo risco e liquidez."
)

ranking_columns = [
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
    column for column in ranking_columns if column in ranking_view.columns
]

st.dataframe(
    ranking_view[available_ranking_columns].style.format(
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


st.subheader(f"Carteira Quantitativa Top {top_n_quant}")

st.write("Ações selecionadas automaticamente pelo ranking quantitativo preliminar:")

portfolio_columns = [
    "score_momentum",
    "score_risco",
    "score_liquidez",
    "score_preliminar",
]

available_portfolio_columns = [
    column for column in portfolio_columns if column in ranking_view.columns
]

st.dataframe(
    ranking_view.head(top_n_quant)[available_portfolio_columns].style.format(
        {
            "score_momentum": "{:.2f}",
            "score_risco": "{:.2f}",
            "score_liquidez": "{:.2f}",
            "score_preliminar": "{:.2f}",
        }
    ),
    use_container_width=True,
)


if quant_portfolio:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Retorno Total", f"{quant_portfolio['total_return']:.2%}")
    col2.metric("CAGR", f"{quant_portfolio['cagr']:.2%}")
    col3.metric("Volatilidade", f"{quant_portfolio['volatility']:.2%}")
    col4.metric("Max Drawdown", f"{quant_portfolio['max_drawdown']:.2%}")

    col5, col6 = st.columns(2)
    col5.metric("Sharpe Ratio", f"{quant_portfolio['sharpe']:.2f}")
    col6.metric("Ações no Top Ranking", len(top_quant_tickers))
else:
    st.warning("Não foi possível calcular a carteira quantitativa.")


st.subheader("Desempenho Relativo")

performance_df = normalized_prices.copy()

if manual_portfolio:
    performance_df["Carteira Manual Equal Weight"] = manual_portfolio["curve"]

if quant_portfolio:
    performance_df[f"Carteira Quant Top {top_n_quant}"] = quant_portfolio["curve"]

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