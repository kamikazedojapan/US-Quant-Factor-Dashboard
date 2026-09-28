from pathlib import Path

import pandas as pd

SOURCE_URL = ("https://raw.githubusercontent.com/"
              "datasets/s-and-p-500-companies/"
              "main/data/constituents.csv")

OUTPUT_PATH = Path("data/tickers_sp500.csv")

def normalize_yfinance_ticker(ticker):
  """
  Normaliza símbolos para o padrão utilizado pelo Yahoo Finance.

    Exemplos:
    BRK.B -> BRK-B
    BF.B  -> BF-B
  """
  if pd.isna(ticker):
    return pd.NA

  return (
    str(ticker)
    .strip()
    .upper()
    .replace(".", "-")
  )

def load_sp500_source():
  """
  Baixa lista atual de constituintes do S&P500
  """

  return pd.read_csv(SOURCE_URL)

def transform_sp500_data(source_df):
  """
  Converte as colunas da fonte para o padrão utilizado pelo projeto
  """

  required_columns = [
    "Symbol",
    "Security",
    "GICS Sector",
    "GICS Sub-Industry",
  ]

  missing_columns = [
    column
    for column in required_columns
    if column not in source_df.columns
  ]

  if missing_columns:
    raise ValueError(
      f"Colunas obrigatórias ausentes {missing_columns}"
    )

  universe_df = pd.DataFrame(
    {
      "ticker": source_df["Symbol"].apply(
        normalize_yfinance_ticker
      ),
      "company": source_df["Security"].astype("string").str.strip(),
      "sector": source_df["GICS Sector"].astype("string").str.strip(),
      "industry": (
        source_df["GICS Sub-Industry"]
        .astype("string")
        .str.strip()
      ),
    }
  )

  return universe_df

def validate_sp500_data(universe_df):
  """
  Valida o universo antes de substituir o CSV atual.
  """

  required_columns = [
    "ticker",
    "company",
    "sector",
    "industry",
  ]

  if list(universe_df.columns) != required_columns:
    raise ValueError(
      "A estrutura final do CSV está incorreta."
    )

  if universe_df.empty:
    raise ValueError(
      "O universo retornado está vazio."
    )

  duplicated_tickers = universe_df[
    universe_df["ticker"].duplicated()
  ]

  if not duplicated_tickers.empty:
    raise ValueError(
      "Foram encontrados tickers duplicados."
    )

  normalized_fields = universe_df[required_columns].astype("string").apply(
    lambda column: column.str.strip()
  )

  invalid_rows = (
    universe_df[required_columns].isna().any(axis=1)
    | normalized_fields.eq("").fillna(False).any(axis=1)
  )

  empty_fields = universe_df[invalid_rows]

  if not empty_fields.empty:
    raise ValueError(
      "Foram encontrados registros com o campo vazio"
    )

  if len(universe_df) < 450:
    raise ValueError(
      f"Quantidade inesperadamente baixa de constituintes: "
      f"{len(universe_df)}"
    )

def save_sp500_data(universe_df):
  """
  Salva o universo validado no arquivo utilizado pelo dashboard.
  """

  OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
  )

  universe_df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8",
  )

def update_sp500_tickers():
  """
  Executa todo o processo de atualização do universo.
  """

  print("Baixando lista do S&P 500...")

  source_df = load_sp500_source()

  print(
    f"Registros recebidos da fonte> {len(source_df)}"
  )

  universe_df = transform_sp500_data(
    source_df
  )

  universe_df = universe_df.drop_duplicates(
    subset=["ticker"],
    keep="first",
  )

  universe_df = universe_df.sort_values(
    "ticker"
  ).reset_index(drop=True)

  print("Colunas encontradas:")

  print(universe_df.columns.to_list())

  validate_sp500_data(
    universe_df
  )

  print("\nDistribuição por setor:")
  print(
    universe_df["sector"]
    .value_counts()
    .sort_index()
  )

  save_sp500_data(
    universe_df
  )

  print(
    f"\nArquivo atualizado: {OUTPUT_PATH}"
  )

  print(
    f"Total de tickers salvos: {len(universe_df)}"
  )

if __name__ == "__main__":
  update_sp500_tickers()