import pandas as pd

from src.universe import select_balanced_tickers_by_sector

def test_returns_empty_list_for_empty_dataframe():
  stocks_df = pd.DataFrame(
    columns=[
      "ticker",
      "sector",
    ]
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=10,
  )

  assert result == []

def test_selects_tickers_balanced_across_selectors():
  stocks_df = pd.DataFrame(
    {
      "ticker": [
        "TECH2",
        "HEALTH2",
        "ENERGY1",
        "TECH1",
        "HEALTH1",
      ],
      "sector": [
        "Technology",
        "Health Care",
        "Energy",
        "Technology",
        "Health Care",
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=4,
  )

  assert result == [
    "ENERGY1",
    "HEALTH1",
    "TECH1",
    "HEALTH2",
  ]

def test_normalizes_and_removes_duplicate_tickers():
  stocks_df = pd.DataFrame(
    {
      "ticker": [
        " aapl",
        "AAPL",
        " msft",
      ],
      "sector": [
        "Technology",
        "Technology",
        "Technology",
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=10,
  )

  assert result == [
    "AAPL",
    "MSFT",
  ]

def test_respects_max_tickers():
  stock_df = pd.DataFrame(
    {
      "ticker": [
        "AAA",
        "BBB",
        "CCC",
        "DDD",
        "EEE",
      ],
      "sector": [
        "Technology",
        "Financials",
        "Health Care",
        "Energy",
        "Industrials",
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stock_df,
    max_tickers=3.
  )

  assert len(result) == 3

def test_ignores_sem_setor():
  stocks_df = pd.DataFrame(
    {
      "ticker": [
        "AAPL",
        "MSFT",
        "XYZ",
      ],
      "sector": [
        "Technology",
        "Technology",
        "Sem setor",
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=10,
  )

  assert result == [
    "AAPL",
    "MSFT",
  ]

def test_ignores_empty_sector():
  stocks_df = pd.DataFrame(
    {
      "ticker": [
        "AAPL",
        "MSFT",
      ],
      "sector": [
        "Technology",
        "",
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=10,
  )

  assert result == ["AAPL"]

def test_ignores_missing_sector():
  stocks_df = pd.DataFrame(
    {
      "ticker": [
        "AAPL",
        "MSFT",
      ],
      "sector": [
        "Technology",
        None,
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=10,
  )

  assert result == ["AAPL"]

def test_ignores_missing_ticker():
  stocks_df = pd.DataFrame(
    {
      "ticker": [
        "AAPL",
        None,
      ],
      "sector": [
        "Technology",
        "Financials",
      ],
    }
  )

  result = select_balanced_tickers_by_sector(
    stocks_df=stocks_df,
    max_tickers=10,
  )

  assert result == ["AAPL"]