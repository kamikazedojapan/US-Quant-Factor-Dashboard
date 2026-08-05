import pandas as pd
import streamlit as st
import yfinance as yf

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