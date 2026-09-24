"""
Funções para seleção e organização do universo de ações.
"""


def select_balanced_tickers_by_sector(
  stocks_df,
  max_tickers,
  ticker_column="ticker",
  sector_column="sector",
):
  """
  Seleciona tickers de forma balanceada entre setores.

  A função percorre os setores em ciclos, pegando um ticker por setor
  até atingir o limite definido em max_tickers.

  Isso evita que os modos Rápido, Médio, Amplo e Grande peguem apenas
  os primeiros tickers em ordem alfabética.
  """

  if stocks_df.empty:
    return []

  clean_df = stocks_df[
    [
      ticker_column,
      sector_column,
    ]
  ].copy()

  clean_df[ticker_column] = clean_df[ticker_column].astype(str).str.upper().str.strip()

  clean_df[sector_column] = clean_df[sector_column].astype(str).str.strip()

  clean_df = clean_df[
    (clean_df[ticker_column] != "")
    & (clean_df[sector_column] != "")
    & (clean_df[sector_column] != "Sem setor")
  ]

  clean_df = clean_df.drop_duplicates(
    subset=[ticker_column],
    keep="first",
  )

  clean_df = clean_df.sort_values(
    [
      sector_column,
      ticker_column,
    ]
  )

  all_tickers = clean_df[ticker_column].tolist()

  if max_tickers >= len(all_tickers):
    return all_tickers

  sector_groups = {
    sector: group[ticker_column].tolist()
    for sector, group in clean_df.groupby(
      sector_column,
      sort=True,
    )
  }

  selected_tickers = []

  while len(selected_tickers) < max_tickers and sector_groups:
    for sector in list(sector_groups.keys()):
      if len(selected_tickers) >= max_tickers:
        break

      tickers_from_sector = sector_groups[sector]

      if tickers_from_sector:
        selected_tickers.append(tickers_from_sector.pop(0))

      if not tickers_from_sector:
        del sector_groups[sector]

  return selected_tickers
