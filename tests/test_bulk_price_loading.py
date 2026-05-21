import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import market_cache
from market_cache import load_price_data_bulk, save_price_data_bulk
from market_data import download_data_bulk, normalize_downloaded_data
from portfolio_scanner import load_scanner_price_data_bulk, scan_market
from portfolio_backtest import (
    build_price_data_session_key,
    load_market_price_data
)


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

    def test_price_cache_treats_recent_market_close_as_fresh(self):
        recent_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=2)
        save_price_data_bulk(
            {
                "AAA": pd.DataFrame({
                    "date": [recent_date],
                    "open": [10.0],
                    "high": [11.0],
                    "low": [9.0],
                    "close": [10.5],
                    "volume": [1000],
                }),
            },
            interval="1d"
        )

        _, status = load_price_data_bulk(["AAA"], interval="1d")

        self.assertEqual(status["AAA"]["status"], "loaded")

    def test_save_price_data_bulk_upserts_without_deleting_history(self):
        save_price_data_bulk(
            {
                "AAA": pd.DataFrame({
                    "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
                    "open": [10.0, 11.0],
                    "high": [12.0, 13.0],
                    "low": [9.0, 10.0],
                    "close": [11.0, 12.0],
                    "volume": [1000, 1100],
                }),
            },
            interval="1d"
        )
        save_price_data_bulk(
            {
                "AAA": pd.DataFrame({
                    "date": pd.to_datetime(["2026-01-02", "2026-01-03"]),
                    "open": [20.0, 30.0],
                    "high": [21.0, 31.0],
                    "low": [19.0, 29.0],
                    "close": [20.5, 30.5],
                    "volume": [2000, 3000],
                }),
            },
            interval="1d"
        )

        data_by_ticker, _ = load_price_data_bulk(["AAA"], interval="1d")
        price_data = data_by_ticker["AAA"]

        self.assertEqual(
            price_data["date"].dt.strftime("%Y-%m-%d").tolist(),
            ["2026-01-01", "2026-01-02", "2026-01-03"]
        )
        self.assertEqual(price_data["close"].tolist(), [11.0, 20.5, 30.5])

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

    def test_normalize_downloaded_data_renames_datetime_index_to_date(self):
        raw_data = pd.DataFrame(
            {
                "Open": [10.0, 11.0],
                "High": [12.0, 13.0],
                "Low": [9.0, 10.0],
                "Close": [11.0, 12.0],
                "Volume": [1000, 1100],
            },
            index=pd.DatetimeIndex(
                pd.to_datetime(["2026-01-01 09:00", "2026-01-01 09:05"]),
                name="Datetime"
            )
        )

        normalized = normalize_downloaded_data(raw_data)

        self.assertIn("date", normalized.columns)
        self.assertNotIn("datetime", normalized.columns)
        self.assertEqual(len(normalized), 2)
        self.assertEqual(normalized["close"].tolist(), [11.0, 12.0])

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

    @patch("portfolio_backtest.download_data_bulk")
    @patch("portfolio_backtest.load_price_data_bulk")
    def test_load_market_price_data_refreshes_stale_incrementally(
        self,
        mock_load_bulk,
        mock_download_bulk
    ):
        cached_data = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "open": [10.0, 11.0],
            "high": [12.0, 13.0],
            "low": [9.0, 10.0],
            "close": [11.0, 12.0],
            "volume": [1000, 1100],
        })
        downloaded_data = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-02", "2026-01-03"]),
            "open": [20.0, 30.0],
            "high": [21.0, 31.0],
            "low": [19.0, 29.0],
            "close": [20.5, 30.5],
            "volume": [2000, 3000],
        })
        mock_load_bulk.return_value = (
            {"AAA": cached_data},
            {"AAA": {"status": "stale", "last_date": "2026-01-02"}}
        )
        mock_download_bulk.return_value = ({"AAA": downloaded_data}, [])

        price_data_by_ticker, metadata = load_market_price_data(
            ["AAA"],
            return_metadata=True
        )

        mock_download_bulk.assert_called_once()
        self.assertEqual(
            mock_download_bulk.call_args.kwargs["start"],
            "2025-12-26"
        )
        self.assertEqual(metadata["downloaded"], 1)
        self.assertEqual(
            price_data_by_ticker["AAA"]["date"].dt.strftime("%Y-%m-%d").tolist(),
            ["2026-01-01", "2026-01-02", "2026-01-03"]
        )
        self.assertEqual(
            price_data_by_ticker["AAA"]["close"].tolist(),
            [11.0, 20.5, 30.5]
        )

    @patch("portfolio_scanner.download_data_bulk")
    @patch("portfolio_scanner.load_price_data_bulk")
    def test_load_scanner_price_data_bulk_downloads_missing_full_period(
        self,
        mock_load_bulk,
        mock_download_bulk
    ):
        downloaded_data = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01"]),
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000],
        })
        mock_load_bulk.return_value = (
            {},
            {"AAA": {"status": "missing", "last_date": None}}
        )
        mock_download_bulk.return_value = ({"AAA": downloaded_data}, [])

        price_data_by_ticker, failed = load_scanner_price_data_bulk(["AAA"])

        mock_download_bulk.assert_called_once()
        self.assertEqual(mock_download_bulk.call_args.kwargs["period"], "5y")
        self.assertNotIn("start", mock_download_bulk.call_args.kwargs)
        self.assertEqual(set(price_data_by_ticker), {"AAA"})
        self.assertEqual(failed, [])

    @patch("portfolio_scanner.download_data")
    @patch("portfolio_scanner.download_data_bulk")
    @patch("portfolio_scanner.load_price_data_bulk")
    def test_scan_market_uses_bulk_loader_by_default(
        self,
        mock_load_bulk,
        mock_download_bulk,
        mock_download
    ):
        dates = pd.date_range("2025-01-01", periods=260, freq="B")
        price_data = pd.DataFrame({
            "date": dates,
            "open": [100.0] * len(dates),
            "high": [101.0] * len(dates),
            "low": [99.0] * len(dates),
            "close": [100.0] * len(dates),
            "volume": [1000] * len(dates),
        })
        mock_load_bulk.return_value = (
            {"AAA": price_data},
            {"AAA": {"status": "loaded"}}
        )
        mock_download_bulk.return_value = ({}, [])

        scanner = scan_market(["AAA"])

        self.assertFalse(scanner.empty)
        mock_download.assert_not_called()
        mock_download_bulk.assert_not_called()

    @patch("portfolio_scanner.download_data_bulk")
    @patch("portfolio_scanner.load_price_data_bulk")
    def test_scan_market_cache_only_does_not_download_missing(
        self,
        mock_load_bulk,
        mock_download_bulk
    ):
        mock_load_bulk.return_value = (
            {},
            {"AAA": {"status": "missing"}}
        )

        scanner = scan_market(["AAA"], download_missing=False)

        self.assertFalse(scanner.empty)
        self.assertEqual(scanner.iloc[0]["data_status"], "NO_DATA")
        mock_download_bulk.assert_not_called()

    @patch("portfolio_backtest.download_data_bulk")
    @patch("portfolio_backtest.load_price_data_bulk")
    def test_load_market_price_data_cache_only_does_not_download_stale(
        self,
        mock_load_bulk,
        mock_download_bulk
    ):
        cached_data = pd.DataFrame({
            "date": pd.to_datetime(["2026-01-01"]),
            "open": [10.0],
            "high": [11.0],
            "low": [9.0],
            "close": [10.5],
            "volume": [1000],
        })
        mock_load_bulk.return_value = (
            {"AAA": cached_data},
            {"AAA": {"status": "stale", "last_date": "2026-01-01"}}
        )

        price_data_by_ticker, metadata = load_market_price_data(
            ["AAA"],
            download_missing=False,
            return_metadata=True
        )

        self.assertEqual(set(price_data_by_ticker), {"AAA"})
        self.assertEqual(metadata["download_missing"], False)
        self.assertEqual(metadata["downloaded"], 0)
        mock_download_bulk.assert_not_called()


if __name__ == "__main__":
    unittest.main()
