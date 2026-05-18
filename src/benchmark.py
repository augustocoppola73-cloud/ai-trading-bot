import pandas as pd


def calculate_buy_and_hold(
    df: pd.DataFrame,
    initial_capital: float
) -> dict:

    df = df.copy()

    first_price = df.iloc[0]["close"]
    shares = initial_capital / first_price

    df["buy_hold_equity"] = df["close"] * shares
    df["buy_hold_peak"] = df["buy_hold_equity"].cummax()

    df["buy_hold_drawdown_%"] = (
        (df["buy_hold_equity"] - df["buy_hold_peak"])
        / df["buy_hold_peak"]
    ) * 100

    final_value = df.iloc[-1]["buy_hold_equity"]

    total_return = (
        (final_value - initial_capital)
        / initial_capital
    ) * 100

    max_drawdown = df["buy_hold_drawdown_%"].min()

    return {
        "buy_hold_final_capital": round(final_value, 2),
        "buy_hold_return_%": round(total_return, 2),
        "buy_hold_max_drawdown_%": round(max_drawdown, 2)
    }