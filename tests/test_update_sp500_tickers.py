import pandas as pd
import pytest

import scripts.update_sp500_tickers as updater

from scripts.update_sp500_tickers import (
  normalize_yfinance_ticker,
  transform_sp500_data,
)

def test_normalize_yfinance_ticker_replaces_dot():
  result = normalize_yfinance_ticker("BRK.B")

  assert result == "BRK-B"

def test_normalize_yfinance_ticker_strips_spaces():
  result = normalize_yfinance_ticker(  "aapl  ")

  assert result == "AAPL"

def test_normalize_yfinance_ticker_handle_already_normalized_symbol():
  result = normalize_yfinance_ticker("MSFT")

  assert result == "MSFT"

def test_normalize_yfinance_ticker_handles_second_class_share_example():
  result = normalize_yfinance_ticker("BF.B")

  assert result == "BF-B"

def test_transform_sp500_data_creates_expected_columns():
  source_df = pd.DataFrame(
    {
      "Symbol": ["AAPL", "BRK.B"],
      "Security": ["Apple Inc.", "Berkshire Hathaway"],
      "GICS Sector": [
        "Information Technology",
        "Financials",
      ],
      "GICS Sub-Industry": [
        "Technology Hardware",
        "Multi-Sector Holdings",
      ],
    }
  )

  result = transform_sp500_data(source_df)

  assert list(result.columns) == [
    "ticker",
    "company",
    "sector",
    "industry",
  ]

  assert result["ticker"].tolist() == [
    "AAPL",
    "BRK-B"
  ]

def test_transform_sp500_data_strips_text_fields():
  source_df = pd.DataFrame(
    {
      "Symbol": [" aapl "],
      "Security": [" Apple Inc. "],
      "GICS Sector": [" Information Technology "],
      "GICS Sub-Industry": [" Technology Hardware "],
    }
  )

  result = transform_sp500_data(source_df)

  assert result.loc[0, "ticker"] == "AAPL"
  assert result.loc[0, "company"] == "Apple Inc."
  assert result.loc[0, "sector"] == "Information Technology"
  assert result.loc[0, "industry"] == "Technology Hardware"

def test_transform_sp500_data_raises_when_required_column_is_missing():
  source_df = pd.DataFrame(
    {
      "Symbol": ["AAPL"],
      "Security": ["Apple Inc."],
      "GICS Sector": ["Information Technology"],
    }
  )

  with pytest.raises(ValueError):
    transform_sp500_data(source_df)


def make_valid_universe(size=500):
  return pd.DataFrame(
    {
      "ticker": [f"T{i:03d}" for i in range(size)],
      "company": [f"Company {i}" for i in range(size)],
      "sector": ["Technology"] * size,
      "industry": ["Software"] * size,
    }
  )


def make_source(size=500):
  return pd.DataFrame(
    {
      "Symbol": [f"T{i:03d}" for i in range(size)],
      "Security": [f"Company {i}" for i in range(size)],
      "GICS Sector": ["Technology"] * size,
      "GICS Sub-Industry": ["Software"] * size,
    }
  )


def test_validate_accepts_valid_universe():
  updater.validate_sp500_data(make_valid_universe())


def test_validate_rejects_wrong_columns():
  df = make_valid_universe().drop(columns=["industry"])
  with pytest.raises(ValueError):
    updater.validate_sp500_data(df)


def test_validate_rejects_empty_universe():
  df = pd.DataFrame(columns=["ticker", "company", "sector", "industry"])
  with pytest.raises(ValueError):
    updater.validate_sp500_data(df)


def test_validate_rejects_duplicate_tickers():
  df = make_valid_universe()
  df.loc[1, "ticker"] = df.loc[0, "ticker"]
  with pytest.raises(ValueError):
    updater.validate_sp500_data(df)


def test_validate_rejects_missing_values():
  df = make_valid_universe()
  df.loc[10, "sector"] = None
  with pytest.raises(ValueError):
    updater.validate_sp500_data(df)


def test_validate_rejects_small_universe():
  with pytest.raises(ValueError):
    updater.validate_sp500_data(make_valid_universe(100))


def test_validate_rejects_blank_strings():
  df = make_valid_universe()
  df.loc[10, "sector"] = "   "
  with pytest.raises(ValueError):
    updater.validate_sp500_data(df)


def test_transform_preserves_missing_values_for_validation():
  source = make_source()
  source.loc[10, "GICS Sector"] = None
  transformed = updater.transform_sp500_data(source)
  with pytest.raises(ValueError):
    updater.validate_sp500_data(transformed)


def test_save_sp500_data_writes_expected_csv(tmp_path, monkeypatch):
  output = tmp_path / "nested" / "tickers_sp500.csv"
  monkeypatch.setattr(updater, "OUTPUT_PATH", output)
  df = make_valid_universe()

  updater.save_sp500_data(df)

  assert output.exists()
  saved = pd.read_csv(output)
  pd.testing.assert_frame_equal(saved, df)


def test_update_pipeline_uses_temp_file_sorts_and_deduplicates(tmp_path, monkeypatch):
  output = tmp_path / "tickers_sp500.csv"
  monkeypatch.setattr(updater, "OUTPUT_PATH", output)

  source = make_source(501)
  duplicate = source.iloc[[0]].copy()
  source = pd.concat([source.iloc[::-1], duplicate], ignore_index=True)
  monkeypatch.setattr(updater, "load_sp500_source", lambda: source)

  updater.update_sp500_tickers()

  assert output.exists()
  saved = pd.read_csv(output)
  assert list(saved.columns) == ["ticker", "company", "sector", "industry"]
  assert len(saved) == 501
  assert saved["ticker"].is_unique
  assert saved["ticker"].tolist() == sorted(saved["ticker"].tolist())


def test_transform_missing_symbol_is_rejected_by_validation():
  source = make_source()
  source.loc[10, "Symbol"] = None
  transformed = updater.transform_sp500_data(source)
  with pytest.raises(ValueError):
    updater.validate_sp500_data(transformed)


def test_invalid_update_does_not_overwrite_existing_csv(tmp_path, monkeypatch):
  output = tmp_path / "tickers_sp500.csv"
  original = "ticker,company,sector,industry\nKEEP,Keep Co,Keep,Keep\n"
  output.write_text(original, encoding="utf-8")
  monkeypatch.setattr(updater, "OUTPUT_PATH", output)
  monkeypatch.setattr(updater, "load_sp500_source", lambda: make_source(100))

  with pytest.raises(ValueError):
    updater.update_sp500_tickers()

  assert output.read_text(encoding="utf-8") == original
