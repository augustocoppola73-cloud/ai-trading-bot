import pandas as pd


def calculate_drawdown(equity_curve: pd.DataFrame):

    equity_curve = equity_curve.copy()

    equity_curve["peak"] = equity_curve["equity"].cummax()

    equity_curve["drawdown_%"] = (
        (equity_curve["equity"] - equity_curve["peak"])
        / equity_curve["peak"]
    ) * 100

    max_drawdown = equity_curve["drawdown_%"].min()

    return round(max_drawdown, 2)


def calculate_performance(
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    initial_capital: float,
    final_capital: float
) -> dict:

    total_return = (
        (final_capital - initial_capital)
        / initial_capital
    ) * 100

    closed_trade_types = ["SELL", "STOP_LOSS", "TRAILING_STOP"]

    sell_trades = trades[
        trades["type"].isin(closed_trade_types)
    ].copy()
    
    number_of_trades = len(sell_trades)

    if number_of_trades == 0:

        return {
            "initial_capital": initial_capital,
            "final_capital": final_capital,
            "total_return_%": round(total_return, 2),
            "number_of_trades": 0,
            "win_rate_%": 0,
            "profit_factor": 0,
            "best_trade_%": 0,
            "worst_trade_%": 0,
            "max_drawdown_%": 0
        }

    winning_trades = sell_trades[
        sell_trades["pnl_%"] > 0
    ]

    losing_trades = sell_trades[
        sell_trades["pnl_%"] <= 0
    ]

    win_rate = (
        len(winning_trades)
        / number_of_trades
    ) * 100

    gross_profit = winning_trades["pnl_%"].sum()

    gross_loss = abs(
        losing_trades["pnl_%"].sum()
    )

    profit_factor = (
        gross_profit / gross_loss
        if gross_loss != 0
        else float("inf")
    )

    best_trade = sell_trades["pnl_%"].max()

    worst_trade = sell_trades["pnl_%"].min()

    max_drawdown = calculate_drawdown(
        equity_curve
    )

    return {
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(final_capital, 2),
        "total_return_%": round(total_return, 2),
        "number_of_trades": number_of_trades,
        "win_rate_%": round(win_rate, 2),
        "profit_factor": round(profit_factor, 2),
        "best_trade_%": round(best_trade, 2),
        "worst_trade_%": round(worst_trade, 2),
        "max_drawdown_%": round(max_drawdown, 2)
    }