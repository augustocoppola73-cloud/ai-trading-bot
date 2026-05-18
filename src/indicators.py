import pandas as pd
import pandas_ta as ta

from strategy import merge_strategy_config


def add_indicators(
    df: pd.DataFrame,
    strategy_config: dict | None = None
) -> pd.DataFrame:
    """
    Aggiunge indicatori tecnici al dataframe.
    """
    df = df.copy()
    config = merge_strategy_config(strategy_config)

    df["ema_20"] = ta.ema(df["close"], length=20)
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    df["sma_50"] = ta.sma(df["close"], length=50)
    df["sma_200"] = ta.sma(df["close"], length=200)

    ma_type = config["ma_type"]
    fast_period = int(config["fast_ma_period"])
    slow_period = int(config["slow_ma_period"])
    long_period = int(config["long_ma_period"])

    if ma_type == "SMA":
        df["trend_fast_ma"] = ta.sma(df["close"], length=fast_period)
        df["trend_slow_ma"] = ta.sma(df["close"], length=slow_period)
        df["trend_long_ma"] = ta.sma(df["close"], length=long_period)
    else:
        df["trend_fast_ma"] = ta.ema(df["close"], length=fast_period)
        df["trend_slow_ma"] = ta.ema(df["close"], length=slow_period)
        df["trend_long_ma"] = ta.ema(df["close"], length=long_period)

    df["rsi"] = ta.rsi(df["close"], length=int(config["rsi_period"]))

    bollinger = ta.bbands(df["close"], length=20, std=2)

    if bollinger is not None:
        bb_columns = {
            column[:3]: column
            for column in bollinger.columns
        }
        df["bb_lower"] = bollinger[bb_columns["BBL"]]
        df["bb_middle"] = bollinger[bb_columns["BBM"]]
        df["bb_upper"] = bollinger[bb_columns["BBU"]]
        df["bb_bandwidth"] = bollinger.get(
            bb_columns.get("BBB"),
            ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]) * 100
        )
        df["bb_percent_b"] = bollinger.get(
            bb_columns.get("BBP"),
            (df["close"] - df["bb_lower"]) /
            (df["bb_upper"] - df["bb_lower"])
        )
    else:
        df["bb_lower"] = None
        df["bb_middle"] = None
        df["bb_upper"] = None
        df["bb_bandwidth"] = None
        df["bb_percent_b"] = None

    df["atr"] = ta.atr(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=int(config["atr_period"])
    )

    adx = ta.adx(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        length=int(config["adx_period"])
    )
    adx_column = f"ADX_{int(config['adx_period'])}"
    df["adx"] = adx[adx_column] if adx is not None else None

    macd = ta.macd(
        close=df["close"],
        fast=int(config["macd_fast"]),
        slow=int(config["macd_slow"]),
        signal=int(config["macd_signal"])
    )

    if macd is not None:
        macd_suffix = (
            f"{int(config['macd_fast'])}_"
            f"{int(config['macd_slow'])}_"
            f"{int(config['macd_signal'])}"
        )
        df["macd"] = macd[f"MACD_{macd_suffix}"]
        df["macd_signal"] = macd[f"MACDs_{macd_suffix}"]
        df["macd_hist"] = macd[f"MACDh_{macd_suffix}"]
    else:
        df["macd"] = None
        df["macd_signal"] = None
        df["macd_hist"] = None

    df["volume_sma_20"] = ta.sma(
        df["volume"],
        length=int(config["volume_sma_period"])
    )
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"]

    df["uptrend"] = (
        (df["trend_fast_ma"] > df["trend_slow_ma"]) &
        (df["close"] > df["trend_long_ma"])
    )

    conditions = [
        (df["trend_fast_ma"] > df["trend_slow_ma"]) &
        (df["close"] > df["trend_long_ma"]),
        (df["trend_fast_ma"] < df["trend_slow_ma"]) &
        (df["close"] < df["trend_long_ma"])
    ]

    df["market_regime"] = "SIDEWAYS"
    df.loc[conditions[0], "market_regime"] = "BULL"
    df.loc[conditions[1], "market_regime"] = "BEAR"

    return df
