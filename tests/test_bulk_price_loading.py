import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import market_cache
from market_cache import load_price_data_bulk, save_price_data_bulk
from market_data import download_data_bulk
from portfolio_backtest import build_price_data_session_key


class BulkPriceLoadingTests(unittest.TestCase):
    def setUp(self):
        self.original_cache_path = market_cache.CACHE_PATH
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        market_cache.CACHE_PATH = Path(self.temp_dir.name) / "cache.sqlite"

    def tearDown(self):
        market_cache.CACHE_PATH = self.original_cache_path
        self.temp_dir.cleanup()

    def test_load_price_data_bulk_marks_loaded_missing_and_stale(self):
        fresh_date = pd.Timestamp.today().normalize()
        stale_date = fresh_date - pd.Timedelta(days=10)
        save_price_data_bulk(
            {
                "AAA": pd.DataFrame({
                    "date": [fresh_date],
                    "open": [10.0],
                    "high": [11.0],
                    "low": [9.0],
                    "close": [10.5],
                    "volume": [1000],
                }),
                "BBB": pd.DataFrame({
                    "date": [stale_date],
                    "open": [20.0],
                    "high": [21.0],
                    "low": [19.0],
                    "close": [20.5],
                    "volume": [2000],
                }),
            },
            interval="1d"
        )

        data_by_ticker, status = load_price_data_bulk(
            ["AAA", "BBB", "CCC"],
            interval="1d"
        )

        self.assertEqual(set(data_by_ticker), {"AAA", "BBB"})
        self.assertEqual(status["AAA"]["status"], "loaded")
        self.assertEqual(status["BBB"]["status"], "stale")
        self.assertEqual(status["CCC"]["status"], "missing")

    @patch("market_data.save_price_data_bulk")
    @patch("market_data.yf.download")
    def test_download_data_bulk_normalizes_multi_ticker_response(
        self,
        mock_download,
        mock_save_bulk
    ):
        dates = pd.to_datetime(["2026-01-01", "2026-01-02"])
        mock_download.return_value = pd.DataFrame(
            {
                ("AAA", "Open"): [10.0, 11.0],
                ("AAA", "High"): [12.0, 13.0],
                ("AAA", "Low"): [9.0, 10.0],
                ("AAA", "Close"): [11.0, 12.0],
                ("AAA", "Volume"): [1000, 1100],
                ("BBB", "Open"): [20.0, 21.0],
                ("BBB", "High"): [22.0, 23.0],
                ("BBB", "Low"): [19.0, 20.0],
                ("BBB", "Close"): [21.0, 22.0],
                ("BBB", "Volume"): [2000, 2100],
            },
            index=dates
        )

        downloaded, failed = download_data_bulk(["AAA", "BBB"], batch_size=50)

        self.assertEqual(set(downloaded), {"AAA", "BBB"})
        self.assertEqual(failed, [])
        self.assertIn("close", downloaded["AAA"].columns)
        mock_save_bulk.assert_called_once()

    def test_price_data_session_key_is_order_insensitive(self):
        first_key = build_price_data_session_key(
            ["AAA", "BBB"],
            freshness_date="2026-05-14"
        )
        second_key = build_price_data_session_key(
            ["BBB", "AAA", "AAA"],
            freshness_date="2026-05-14"
        )
        third_key = build_price_data_session_key(
            ["AAA", "CCC"],
            freshness_date="2026-05-14"
        )

        self.assertEqual(first_key, second_key)
        self.assertNotEqual(first_key, third_key)


if __name__ == "__main__":
    unittest.main()
