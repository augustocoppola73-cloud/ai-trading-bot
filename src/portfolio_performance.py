import pandas as pd


def calculate_portfolio_performance(
    portfolio_history: pd.DataFrame,
    initial_capital: float,
    final_capital: float
):

    if portfolio_history is None or portfolio_history.empty:
        return {
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(final_capital, 2),
            "total_return_%": round(
                ((final_capital - initial_capital) / initial_capital) * 100,
                2
            ),
            "max_drawdown_%": 0,
            "weekly_win_rate_%": 0,
            "best_week_%": 0,
            "worst_week_%": 0,
            "rotations": 0,
            "cash_weeks": 0,
            "cash_time_%": 0
        }

    history = portfolio_history.copy()

    if "capital" not in history.columns:
        return {
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(final_capital, 2),
            "total_return_%": round(
                ((final_capital - initial_capital) / initial_capital) * 100,
                2
            ),
            "max_drawdown_%": 0,
            "weekly_win_rate_%": 0,
            "best_week_%": 0,
            "worst_week_%": 0,
            "rotations": 0,
            "cash_weeks": 0,
            "cash_time_%": 0
        }

    total_return = (
        (final_capital - initial_capital)
        / initial_capital
    ) * 100

    history["peak"] = history["capital"].cummax()

    history["drawdown_%"] = (
        (history["capital"] - history["peak"])
        / history["peak"]
    ) * 100

    max_drawdown = history["drawdown_%"].min()

    if "weekly_return_%" in history.columns:
        returns = history["weekly_return_%"].fillna(0)
    else:
        returns = history["capital"].pct_change().fillna(0) * 100

    positive_weeks = returns[returns > 0]
    total_weeks = len(returns)

    win_rate = (
        len(positive_weeks) / total_weeks
    ) * 100 if total_weeks > 0 else 0

    best_week = returns.max() if total_weeks > 0 else 0
    worst_week = returns.min() if total_weeks > 0 else 0
    cash_weeks = 0
    rotations = 0

    if "ticker" in history.columns:
        cash_weeks = int((history["ticker"] == "CASH").sum())
        active_tickers = history["ticker"].replace("CASH", pd.NA).dropna()
        rotations = int((active_tickers != active_tickers.shift()).sum())
        rotations = max(rotations - 1, 0)

    cash_time_pct = (
        (cash_weeks / total_weeks) * 100
        if total_weeks > 0
        else 0
    )

    return {
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(final_capital, 2),
        "total_return_%": round(total_return, 2),
        "max_drawdown_%": round(max_drawdown, 2),
        "weekly_win_rate_%": round(win_rate, 2),
        "best_week_%": round(best_week, 2),
        "worst_week_%": round(worst_week, 2),
        "rotations": rotations,
        "cash_weeks": cash_weeks,
        "cash_time_%": round(cash_time_pct, 2)
    }
