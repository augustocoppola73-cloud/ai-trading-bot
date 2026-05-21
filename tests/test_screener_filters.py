import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from screener_filters import (
    filter_screener_dataframe,
    get_screener_columns,
    get_screener_preset_defaults,
    sort_screener_dataframe,
)


def screener_fixture():
    return pd.DataFrame([
        {
            "watchlist": True,
            "market": "Italy",
            "ticker": "AAA",
            "name": "Alpha",
            "close": 2.5,
            "scanner_score": 130.0,
            "setup_score": 150.0,
            "opportunity_label": "BUY",
            "signal": "BUY",
            "market_regime": "BULL",
            "rsi": 42.0,
            "volatility_%": 2.5,
            "volume_ratio": 1.4,
        },
        {
            "watchlist": False,
            "market": "Italy",
            "ticker": "BBB",
            "name": "Beta",
            "close": 12.0,
            "scanner_score": 80.0,
            "setup_score": 70.0,
            "opportunity_label": "Weak / Avoid",
            "signal": "HOLD",
            "market_regime": "SIDEWAYS",
            "rsi": 28.0,
            "volatility_%": 8.5,
            "volume_ratio": 0.7,
        },
        {
            "watchlist": False,
            "market": "USA",
            "ticker": "CCC",
            "name": "Gamma",
            "close": 4.0,
            "scanner_score": 60.0,
            "setup_score": 20.0,
            "opportunity_label": "SELL / Exit Watch",
            "signal": "SELL",
            "market_regime": "BEAR",
            "rsi": 78.0,
            "volatility_%": 4.0,
            "volume_ratio": 2.1,
        },
    ])


class ScreenerFilterTests(unittest.TestCase):
    def test_filters_price_rsi_volume_and_volatility(self):
        filtered = filter_screener_dataframe(
            screener=screener_fixture(),
            market_filter=["Italy", "USA"],
            search_text="",
            only_watchlist=False,
            signal_filter="ALL",
            regime_filter="ALL",
            opportunity_filter="Tutti",
            min_score=None,
            price_min=0.0,
            price_max=5.0,
            rsi_min=30.0,
            rsi_max=50.0,
            volume_ratio_min=1.0,
            atr_min=0.0,
            atr_max=3.0,
        )

        self.assertEqual(filtered["ticker"].tolist(), ["AAA"])

    def test_preset_defaults_cover_oversold_and_long_candidates(self):
        oversold = get_screener_preset_defaults("RSI ipervenduto")
        long_candidates = get_screener_preset_defaults("Candidati long")

        self.assertEqual(oversold["rsi_max"], 35.0)
        self.assertEqual(long_candidates["signal_filter"], "BUY")
        self.assertEqual(long_candidates["regime_filter"], "BULL")
        self.assertEqual(
            long_candidates["opportunity_filter"],
            "Solo candidati long"
        )

    def test_long_candidate_filter_excludes_sell_and_hold(self):
        filtered = filter_screener_dataframe(
            screener=screener_fixture(),
            market_filter=["Italy", "USA"],
            search_text="",
            only_watchlist=False,
            signal_filter="BUY",
            regime_filter="BULL",
            opportunity_filter="Solo candidati long",
            min_score=0.0,
            price_min=None,
            price_max=None,
            rsi_min=None,
            rsi_max=None,
            volume_ratio_min=None,
            atr_min=None,
            atr_max=None,
        )

        self.assertEqual(filtered["ticker"].tolist(), ["AAA"])

    def test_sort_by_volume_ratio_descending(self):
        sorted_data = sort_screener_dataframe(
            screener_fixture(),
            "Vol Ratio decrescente"
        )

        self.assertEqual(sorted_data["ticker"].tolist()[0], "AAA")
        self.assertEqual(sorted_data["ticker"].tolist()[1], "CCC")

    def test_compact_column_view_keeps_watchlist_and_ticker(self):
        columns = get_screener_columns(screener_fixture(), "Compatta")

        self.assertIn("watchlist", columns)
        self.assertIn("ticker", columns)
        self.assertNotIn("reason", columns)


if __name__ == "__main__":
    unittest.main()
