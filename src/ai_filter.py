import pandas as pd

from strategy import merge_strategy_config


def calculate_ai_score(
    df: pd.DataFrame,
    strategy_config: dict | None = None
) -> pd.DataFrame:

    df = df.copy()
    config = merge_strategy_config(strategy_config)

    fast_ma = df.get("trend_fast_ma", df.get("ema_20"))
    slow_ma = df.get("trend_slow_ma", df.get("ema_50"))
    long_ma = df.get("trend_long_ma", df.get("ema_200"))

    scores = pd.Series(0, index=df.index)

    scores += (fast_ma > slow_ma).astype(int) * 30
    scores += (df["close"] > long_ma).astype(int) * 30
    scores += (
        (df["rsi"] >= config["rsi_buy_min"]) &
        (df["rsi"] <= config["rsi_buy_max"])
    ).astype(int) * 20

    atr_ratio = df["atr"] / df["close"]
    scores += (
        atr_ratio < (config["max_volatility_pct"] / 100)
    ).astype(int) * 20

    if "adx" in df.columns:
        scores += (df["adx"] >= config["adx_min"]).astype(int) * 5

    if "macd_hist" in df.columns:
        scores += (df["macd_hist"] > 0).astype(int) * 5

    if "volume_ratio" in df.columns:
        scores += (
            df["volume_ratio"] >= config["volume_ratio_min"]
        ).astype(int) * 5

    df["ai_score"] = scores

    return df
