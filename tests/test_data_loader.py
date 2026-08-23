import unittest
from unittest.mock import patch

import pandas as pd

from src.data_loader import (
  download_market_data,
  get_sp500_tickers,
)


class TestGetSp500Tickers(unittest.TestCase):
  def setUp(self):
    get_sp500_tickers.clear()

  @patch("src.data_loader.pd.read_csv")
  def test_loads_tickers_from_local_csv(self, mock_read_csv):
    expected = pd.DataFrame(
      {
        "ticker": ["AAPL", "MSFT"],
        "company": ["Apple", "Microsoft"],
      }
    )

    mock_read_csv.return_value = expected

    result = get_sp500_tickers()

    pd.testing.assert_frame_equal(result, expected)

    mock_read_csv.assert_called_once_with(
      "data/tickers_sp500.csv"
    )

  @patch("src.data_loader.st.stop")
  @patch("src.data_loader.st.error")
  @patch(
    "src.data_loader.pd.read_csv",
    side_effect=FileNotFoundError
  )
  def test_reports_missing_ticker_file(
    self,
    mock_read_csv,
    mock_error,
    mock_stop,
  ):
    result = get_sp500_tickers()

    self.assertIsNone(result)

    mock_read_csv.assert_called_once_with(
      "data/tickers_sp500.csv"
    )

    mock_error.assert_called_once_with(
      "Arquivo data/tickers_sp500.csv não encontrado. "
      "Crie o arquivo antes de executar o dashboard."
    )

    mock_stop.assert_called_once_with()


class TestDownloadMarketData(unittest.TestCase):
  def setUp(self):
    download_market_data.clear()

  @patch("src.data_loader.yf.download")
  def test_returns_empty_frames_without_tickers(
    self,
    mock_download,
  ):
    prices, volumes = download_market_data(
      tickers=[],
      start_date="2025-01-01",
      end_date="2025-02-01",
    )

    self.assertTrue(prices.empty)
    self.assertTrue(volumes.empty)
    mock_download.assert_not_called()

  @patch("src.data_loader.yf.download")
  def test_returns_empty_frames_when_download_is_empty(
    self,
    mock_download,
  ):
    mock_download.return_value = pd.DataFrame()

    prices, volumes = download_market_data(
      tickers=["AAPL"],
      start_date="2025-01-01",
      end_date="2025-02-01",
    )

    self.assertTrue(prices.empty)
    self.assertTrue(volumes.empty)

    mock_download.assert_called_once_with(
      ["AAPL"],
      start="2025-01-01",
      end="2025-02-01",
      auto_adjust=True,
      progress=False,
      group_by="column"
    )

  @patch("src.data_loader.yf.download")
  def test_extracts_single_ticker_data(
    self,
    mock_download,
  ):
    dates = pd.to_datetime(
      [
        "2025-01-03",
        "2025-01-01",
        "2025-01-02",
      ]
    )

    mock_download.return_value = pd.DataFrame(
      {
        "Close": [110.0, float("nan"), 100.0],
        "Volume": [1_000.0, float("nan"), 900.0],
      },
      index=dates
    )

    prices, volumes = download_market_data(
      tickers=["AAPL"],
      start_date="2025-01-01",
      end_date="2025-02-01",
    )

    expected_dates = pd.to_datetime(
      [
        "2025-01-02",
        "2025-01-03",
      ]
    )

    expected_prices = pd.DataFrame(
      {
        "AAPL": [100.0, 110.0],
      },
      index=expected_dates,
    )

    expected_volumes = pd.DataFrame(
      {
        "AAPL": [900.0, 1_000.0],
      },
      index=expected_dates,
    )

    pd.testing.assert_frame_equal(
      prices,
      expected_prices,
    )

    pd.testing.assert_frame_equal(
      volumes,
      expected_volumes,
    )

  @patch("src.data_loader.yf.download")
  def test_extracts_multiple_tickers_from_multiindex(
    self,
    mock_download,
  ):
    dates = pd.to_datetime(
      [
        "2025-01-03",
        "2025-01-02",
      ]
    )

    columns = pd.MultiIndex.from_product(
      [
        ["Close", "Volume"],
        ["AAPL", "MSFT"],
      ],
      names=["Price", "Ticker"],
    )

    data = pd.DataFrame(
      [
        [110.0, 220.0, 1_000.0, 2_000.0],
        [100.0, 200.0, 900.0, 1_800.0],
      ],
      index=dates,
      columns=columns
    )

    mock_download.return_value = data

    prices, volumes = download_market_data(
      tickers=["AAPL", "MSFT"],
      start_date="2025-01-01",
      end_date="2025-02-01",
    )

    expected_dates = pd.to_datetime(
      [
        "2025-01-02",
        "2025-01-03",
      ]
    )

    expected_prices = pd.DataFrame(
      {
        "AAPL": [100.0, 110.0],
        "MSFT": [200.0, 220.0],
      },
      index=expected_dates,
    )

    expected_volumes = pd.DataFrame(
      {
        "AAPL": [900.0, 1_000.0],
        "MSFT": [1_800.0, 2_000.0],
      },
      index=expected_dates,
    )

    expected_prices.columns.name = "Ticker"
    expected_volumes.columns.name = "Ticker"

    pd.testing.assert_frame_equal(
      prices,
      expected_prices,
    )

    pd.testing.assert_frame_equal(
      volumes,
      expected_volumes,
    )


if __name__ == "__main__":
  unittest.main()