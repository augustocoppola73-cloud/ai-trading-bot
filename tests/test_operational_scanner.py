import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from date_ranges import get_start_date_for_range
from indicators import add_indicators
from portfolio_scanner import (
    build_buy_gate_context,
    build_scanner_row,
    scan_market_from_price_data,
)


def scanner_latest(**overrides):
    base = {
        "date": pd.Timestamp("2026-05-15"),
        "close": 100.0,
        "atr": 2.0,
        "ai_score": 95,
        "market_regime": "BULL",
        "signal": "BUY",
        "rsi": 62.0,
        "trend_fast_ma": 105.0,
        "trend_slow_ma": 100.0,
        "adx": 28.0,
        "macd": 1.2,
        "macd_hist": 0.4,
        "volume_ratio": 1.2,
        "bb_lower": 90.0,
        "bb_middle": 100.0,
        "bb_upper": 110.0,
        "bb_bandwidth": 20.0,
        "bb_percent_b": 0.65,
    }
    base.update(overrides)

    return pd.Series(base)


class OperationalScannerTests(unittest.TestCase):
    def test_bollinger_columns_are_added(self):
        dates = pd.date_range("2026-01-01", periods=60, freq="B")
        data = pd.DataFrame({
            "date": dates,
            "open": range(100, 160),
            "high": range(101, 161),
            "low": range(99, 159),
            "close": range(100, 160),
            "volume": [1000] * len(dates),
        })

        enriched = add_indicators(
            data,
            strategy_config={
                "fast_ma_period": 5,
                "slow_ma_period": 10,
                "long_ma_period": 20,
            }
        )

        for column in [
            "bb_lower",
            "bb_middle",
            "bb_upper",
            "bb_bandwidth",
            "bb_percent_b",
        ]:
            self.assertIn(column, enriched.columns)

        self.assertTrue(enriched["bb_middle"].dropna().any())
        self.assertTrue(enriched["bb_bandwidth"].dropna().ge(0).all())

    def test_strong_buy_candidate_gets_operational_fields(self):
        row = build_scanner_row("AAA", scanner_latest())

        self.assertEqual(row["data_ultima_chiusura"], "2026-05-15")
        self.assertIn(row["opportunity_label"], ["Strong BUY", "BUY"])
        self.assertGreater(row["setup_score"], row["scanner_score"])
        self.assertIn("Bollinger", row["reason"])
        self.assertTrue(row["buy_gate_passed"])
        self.assertEqual(row["selection_score"], row["scanner_score"])
        self.assertEqual(row["label_score"], row["setup_score"])
        self.assertEqual(row["score_schema_version"], "v1_legacy_additive")

    def test_sell_is_classified_as_exit_watch(self):
        row = build_scanner_row(
            "AAA",
            scanner_latest(signal="SELL", market_regime="BEAR")
        )

        self.assertEqual(row["opportunity_label"], "SELL / Exit Watch")
        self.assertIn("SELL/uscita", row["reason"])
        self.assertFalse(row["buy_gate_passed"])
        self.assertIn("SIGNAL_NOT_BUY", row["buy_gate_fail_reasons"])

    def test_upper_bollinger_extension_penalizes_setup(self):
        balanced = build_scanner_row("AAA", scanner_latest())
        extended = build_scanner_row(
            "AAA",
            scanner_latest(bb_percent_b=1.15)
        )

        self.assertLess(extended["setup_score"], balanced["setup_score"])
        self.assertIn("Bollinger alta", extended["reason"])

    def test_buy_gate_context_explains_exclusions(self):
        row = build_scanner_row(
            "AAA",
            scanner_latest(signal="HOLD", market_regime="SIDEWAYS")
        )
        context = build_buy_gate_context(
            row,
            min_score=120,
            max_volatility_pct=6
        )

        self.assertFalse(context["buy_gate_passed"])
        self.assertIn("SIGNAL_NOT_BUY", context["buy_gate_fail_reasons"])
        self.assertIn("REGIME_NOT_BULL", context["buy_gate_fail_reasons"])

    def test_scan_market_from_price_data_reports_insufficient_history(self):
        short_data = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=20, freq="B"),
            "open": range(20),
            "high": range(1, 21),
            "low": range(20),
            "close": range(1, 21),
            "volume": [1000] * 20,
        })

        scanner = scan_market_from_price_data(
            {"AAA": short_data},
            tickers=["AAA"]
        )

        self.assertEqual(scanner.iloc[0]["data_status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(scanner.iloc[0]["opportunity_label"], "No Data")

    def test_date_range_presets(self):
        end_date = date(2026, 5, 16)

        self.assertEqual(
            get_start_date_for_range(end_date, "1W"),
            date(2026, 5, 9)
        )
        self.assertEqual(
            get_start_date_for_range(end_date, "2W"),
            date(2026, 5, 2)
        )
        self.assertEqual(
            get_start_date_for_range(end_date, "1M"),
            date(2026, 4, 16)
        )
        self.assertEqual(
            get_start_date_for_range(end_date, "3M"),
            date(2026, 2, 16)
        )
        self.assertEqual(
            get_start_date_for_range(end_date, "Ultimo quarto"),
            date(2026, 2, 16)
        )
        self.assertEqual(
            get_start_date_for_range(end_date, "6M"),
            date(2025, 11, 16)
        )
        self.assertEqual(
            get_start_date_for_range(end_date, "1Y"),
            date(2025, 5, 16)
        )



if __name__ == "__main__":
    unittest.main()
