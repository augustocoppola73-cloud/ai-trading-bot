import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_filter import calculate_ai_score
from portfolio_backtest import build_rebalance_scanners, run_portfolio_backtest
from strategy import merge_strategy_config


def calculate_ai_score_with_loop(df, strategy_config=None):
    config = merge_strategy_config(strategy_config)
    scores = []

    for _, row in df.iterrows():
        score = 0
        fast_ma = row.get("trend_fast_ma", row.get("ema_20"))
        slow_ma = row.get("trend_slow_ma", row.get("ema_50"))
        long_ma = row.get("trend_long_ma", row.get("ema_200"))

        if fast_ma > slow_ma:
            score += 30
        if row["close"] > long_ma:
            score += 30
        if config["rsi_buy_min"] <= row["rsi"] <= config["rsi_buy_max"]:
            score += 20

        atr_ratio = row["atr"] / row["close"]
        if atr_ratio < (config["max_volatility_pct"] / 100):
            score += 20
        if row.get("adx", 0) >= config["adx_min"]:
            score += 5
        if row.get("macd_hist", 0) > 0:
            score += 5
        if row.get("volume_ratio", 0) >= config["volume_ratio_min"]:
            score += 5

        scores.append(score)

    return scores


def scanner_fixture(dates):
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "close": [10.0 + index for index, _ in enumerate(dates)],
        "atr": [0.2 for _ in dates],
        "ai_score": [90 for _ in dates],
        "market_regime": ["BULL" for _ in dates],
        "signal": ["BUY" for _ in dates],
        "rsi": [60 for _ in dates],
        "trend_fast_ma": [12.0 for _ in dates],
        "trend_slow_ma": [10.0 for _ in dates],
        "adx": [25 for _ in dates],
        "macd": [1.0 for _ in dates],
        "macd_hist": [0.5 for _ in dates],
        "volume_ratio": [1.2 for _ in dates],
    })


class BacktestScalingTests(unittest.TestCase):
    def test_ai_score_matches_previous_loop_logic(self):
        data = pd.DataFrame({
            "close": [100.0, 90.0, 120.0],
            "atr": [2.0, 8.0, 3.0],
            "rsi": [55.0, 76.0, 65.0],
            "trend_fast_ma": [105.0, 80.0, 130.0],
            "trend_slow_ma": [100.0, 85.0, 125.0],
            "trend_long_ma": [95.0, 95.0, 110.0],
            "adx": [20.0, 10.0, 30.0],
            "macd_hist": [0.4, -0.1, 0.2],
            "volume_ratio": [1.1, 0.5, 0.9],
        })

        expected_scores = calculate_ai_score_with_loop(data)
        scored = calculate_ai_score(data)

        self.assertEqual(scored["ai_score"].tolist(), expected_scores)

    def test_rebalance_scanner_uses_latest_row_before_scan_date(self):
        market_data = {
            "AAA": scanner_fixture(["2024-01-01", "2024-01-03"]),
            "BBB": scanner_fixture(["2024-01-02", "2024-01-04"]),
        }
        rebalance_dates = pd.to_datetime(["2024-01-02", "2024-01-05"])

        scanners = build_rebalance_scanners(market_data, rebalance_dates)

        first_scan = scanners[pd.Timestamp("2024-01-02")]
        aaa_row = first_scan[first_scan["ticker"] == "AAA"].iloc[0]
        bbb_row = first_scan[first_scan["ticker"] == "BBB"].iloc[0]
        self.assertEqual(aaa_row["date"], pd.Timestamp("2024-01-01"))
        self.assertEqual(bbb_row["date"], pd.Timestamp("2024-01-02"))

        second_scan = scanners[pd.Timestamp("2024-01-05")]
        aaa_row = second_scan[second_scan["ticker"] == "AAA"].iloc[0]
        bbb_row = second_scan[second_scan["ticker"] == "BBB"].iloc[0]
        self.assertEqual(aaa_row["date"], pd.Timestamp("2024-01-03"))
        self.assertEqual(bbb_row["date"], pd.Timestamp("2024-01-04"))

    def test_portfolio_backtest_accepts_reused_price_data(self):
        dates = pd.date_range("2023-01-02", periods=320, freq="B")
        price_data_by_ticker = {
            "AAA": pd.DataFrame({
                "date": dates,
                "open": range(100, 420),
                "high": range(101, 421),
                "low": range(99, 419),
                "close": range(100, 420),
                "volume": [1000] * len(dates),
            }),
            "BBB": pd.DataFrame({
                "date": dates,
                "open": [100] * len(dates),
                "high": [101] * len(dates),
                "low": [99] * len(dates),
                "close": [100] * len(dates),
                "volume": [1000] * len(dates),
            }),
        }
        strategy_config = {
            "fast_ma_period": 5,
            "slow_ma_period": 10,
            "long_ma_period": 20,
            "rsi_buy_min": 0,
            "rsi_buy_max": 101,
            "max_volatility_pct": 99,
            "min_ai_score": 0,
            "use_adx_filter": False,
            "use_macd_filter": False,
            "use_volume_filter": False,
        }

        history, final_capital = run_portfolio_backtest(
            tickers=["AAA", "BBB"],
            start_date="2023-09-04",
            end_date="2023-11-06",
            initial_capital=1000,
            min_hold_weeks=1,
            min_scanner_score=0,
            persistence_weeks=1,
            strategy_config=strategy_config,
            price_data_by_ticker=price_data_by_ticker,
        )

        self.assertFalse(history.empty)
        self.assertIn("capital", history.columns)
        self.assertIn("reason", history.columns)
        self.assertGreater(final_capital, 0)


if __name__ == "__main__":
    unittest.main()
