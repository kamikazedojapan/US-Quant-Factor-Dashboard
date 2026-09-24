"""
Atualiza o universo de ações do S&P 500 usado pelo dashboard.

O script baixa uma lista atual de constituintes do S&P 500,
padroniza as colunas para o formato do projeto e salva em:

data/tickers_sp500.csv
"""

from pathlib import Path

import pandas as pd


SOURCE_URL = (
  "https://raw.githubusercontent.com/datasets/"
  "s-and-p-500-companies/main/data/constituents.csv"
)

OUTPUT_PATH = Path("data/tickers_sp500.csv")


def normalize_yfinance_ticker(ticker):
  """
  Converte tickers para o padrão aceito pelo yfinance.

  Exemplo:
  BRK.B -> BRK-B
  BF.B  -> BF-B
  """

  return str(ticker).upper().strip().replace(".", "-")


def update_sp500_tickers():
  """
  Baixa e salva a lista atualizada de constituintes do S&P 500.
  """

  df = pd.read_csv(SOURCE_URL)

  expected_columns = [
    "Symbol",
    "Security",
    "GICS Sector",
    "GICS Sub-Industry",
  ]

  missing_columns = [
    column
    for column in expected_columns
    if column not in df.columns
  ]

  if missing_columns:
      raise ValueError(
        f"Colunas ausentes na fonte de dados: {missing_columns}"
      )

  output_df = pd.DataFrame(
    {
      "ticker": df["Symbol"].apply(normalize_yfinance_ticker),
      "company": df["Security"].astype(str).str.strip(),
      "sector": df["GICS Sector"].astype(str).str.strip(),
      "industry": df["GICS Sub-Industry"].astype(str).str.strip(),
    }
  )

  output_df = output_df.dropna(
    subset=[
      "ticker",
      "company",
      "sector",
      "industry",
    ]
  )

  output_df = output_df.drop_duplicates(
    subset=["ticker"],
    keep="first",
  )

  output_df = output_df.sort_values("ticker").reset_index(drop=True)

  OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
  )

  output_df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8",
  )

  print(f"Arquivo atualizado: {OUTPUT_PATH}")
  print(f"Total de tickers: {len(output_df)}")
  print(output_df.head())


if __name__ == "__main__":
  update_sp500_tickers()