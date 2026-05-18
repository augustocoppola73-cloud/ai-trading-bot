import pandas as pd


DEFAULT_STRATEGY_CONFIG = {
    "ma_type": "EMA",
    "fast_ma_period": 20,
    "slow_ma_period": 50,
    "long_ma_period": 200,
    "rsi_period": 14,
    "rsi_buy_min": 50,
    "rsi_buy_max": 70,
    "rsi_sell_above": 75,
    "atr_period": 14,
    "max_volatility_pct": 6.0,
    "adx_period": 14,
    "adx_min": 18,
    "use_adx_filter": False,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "use_macd_filter": False,
    "volume_sma_period": 20,
    "volume_ratio_min": 0.8,
    "use_volume_filter": False,
    "min_ai_score": 70
}


def merge_strategy_config(strategy_config: dict | None = None) -> dict:
    config = DEFAULT_STRATEGY_CONFIG.copy()

    if isinstance(strategy_config, dict):
        config.update(strategy_config)

    config["ma_type"] = str(config.get("ma_type", "EMA")).upper()

    return config


def generate_signals(
    df: pd.DataFrame,
    strategy_config: dict | None = None
) -> pd.DataFrame:

    df = df.copy()
    config = merge_strategy_config(strategy_config)

    df["signal"] = "HOLD"

    fast_ma_column = "trend_fast_ma"
    slow_ma_column = "trend_slow_ma"
    long_ma_column = "trend_long_ma"

    if fast_ma_column not in df.columns:
        fast_ma_column = "ema_20"
    if slow_ma_column not in df.columns:
        slow_ma_column = "ema_50"
    if long_ma_column not in df.columns:
        long_ma_column = "ema_200"

    volatility_pct = (df["atr"] / df["close"]) * 100

    buy_condition = (
        (df[fast_ma_column] > df[slow_ma_column]) &
        (df["close"] > df[long_ma_column]) &
        (df["rsi"] > config["rsi_buy_min"]) &
        (df["rsi"] < config["rsi_buy_max"]) &
        (df["ai_score"] >= config["min_ai_score"]) &
        (df["market_regime"] == "BULL") &
        (volatility_pct <= config["max_volatility_pct"])
    )

    if config["use_adx_filter"] and "adx" in df.columns:
        buy_condition = buy_condition & (df["adx"] >= config["adx_min"])

    if config["use_macd_filter"] and "macd_hist" in df.columns:
        buy_condition = buy_condition & (df["macd_hist"] > 0)

    if config["use_volume_filter"] and "volume_ratio" in df.columns:
        buy_condition = buy_condition & (
            df["volume_ratio"] >= config["volume_ratio_min"]
        )

    sell_condition = (
        (df[fast_ma_column] < df[slow_ma_column]) |
        (df["rsi"] > config["rsi_sell_above"])
    )

    df.loc[buy_condition, "signal"] = "BUY"

    df.loc[sell_condition, "signal"] = "SELL"

    return df
