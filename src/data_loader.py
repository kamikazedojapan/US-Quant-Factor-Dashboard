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
    tickers_df = pd.read_csv(
      "data/tickers_sp500.csv"
    )

    return tickers_df

  except FileNotFoundError:
    st.error(
      "Arquivo data/tickers_sp500.csv não encontrado. "
      "Crie o arquivo antes de executar o dashboard."
    )
    st.stop()


def extract_market_data(data, tickers):
  """
  Extrai e organiza preços e volumes retornados
  pelo Yahoo Finance.
  """
  if data.empty or not tickers:
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

  prices = (
    prices
    .sort_index()
    .dropna(how="all")
  )

  volumes = (
    volumes
    .sort_index()
    .dropna(how="all")
  )

  return prices, volumes

def chunk_tickers(tickers, chunk_size=50):
  """
  Divide uma lista de tickers em blocos menores.
  """
  for start_index in range(0, len(tickers), chunk_size):
    yield tickers[start_index:start_index + chunk_size]


def download_market_data(tickers, start_date, end_date, chunk_size=50):
  """
  Baixa dados de preço e volume para uma lista de tickers limitada.
  """

  normalized_tickers = tuple(
    sorted(
      set(
        str(ticker).upper().strip()
        for ticker in tickers
        if ticker
      )
    )
  )

  if not normalized_tickers:
    return pd.DataFrame(), pd.DataFrame()

  start_date = pd.Timestamp(start_date).strftime('%Y-%m-%d')
  end_date = pd.Timestamp(end_date).strftime('%Y-%m-%d')

  return _download_market_data_cached(
    tickers=normalized_tickers,
    start_date=start_date,
    end_date=end_date,
    chunk_size=chunk_size,
  )

@st.cache_data(ttl=3600, show_spinner=False)
def _download_market_data_cached(
  tickers,
  start_date,
  end_date,
  chunk_size=50,
):
  """
  Versão com cache do download de dados com todos os tickers
  """

  tickers = list(tickers)

  prices_parts = []
  volumes_parts = []

  for ticker_batch in chunk_tickers(
    tickers=tickers,
    chunk_size=chunk_size,
  ):
    data = yf.download(
      ticker_batch,
      start=start_date,
      end=end_date,
      auto_adjust=True,
      progress=False,
      threads=True,
      group_by="column",
    )

    if data.empty:
      continue

    if isinstance(data.columns, pd.MultiIndex):
      if "Close" not in data.columns.get_level_values(0):
        continue

      prices = data["Close"].copy()

      if "Volume" in data.columns.get_level_values(0):
        volumes = data["Volume"].copy()
      else:
        volumes = pd.DataFrame(index=prices.index)

    else:
      ticker = ticker_batch[0]

      if "Close" not in data.columns:
        continue

      prices = data[["Close"]].copy()
      prices.columns = [ticker]

      if "Volume" in data.columns:
        volumes = data[["Volume"]].copy()
        volumes.columns = [ticker]
      else:
        volumes = pd.DataFrame(index=prices.index)

    if isinstance(prices, pd.Series):
      prices = prices.to_frame(name=ticker_batch[0])

    if isinstance(volumes, pd.Series):
      volumes = volumes.to_frame(name=ticker_batch[0])

    prices = prices.dropna(
      axis=1,
      how="all",
    )

    valid_rows = prices.notna().any(axis=1)

    prices = prices.loc[valid_rows].copy()

    volumes = volumes.reindex(
      index=prices.index,
      columns=prices.columns,
    )

    if prices.empty:
      continue

    prices_parts.append(prices)
    volumes_parts.append(volumes)

  if not prices_parts:
    return pd.DataFrame(), pd.DataFrame()

  prices = pd.concat(
    prices_parts,
    axis=1,
  )

  volumes = pd.concat(
    volumes_parts,
    axis=1,
  )

  prices = prices.loc[
    :,
    ~prices.columns.duplicated(),
  ]

  volumes = volumes.loc[
    :,
    ~volumes.columns.duplicated(),
  ]

  prices = prices.sort_index()
  volumes = volumes.sort_index()

  return prices, volumes

download_market_data.clear = _download_market_data_cached.clear