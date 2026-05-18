import pandas as pd

from backtest import run_backtest
from performance import calculate_performance


def optimize_parameters(
    data: pd.DataFrame,
    initial_capital: float = 1000
):

    results = []

    atr_values = [2.0, 2.5, 3.0]
    trailing_values = [2.5, 3.0, 3.5, 4.0]

    for atr_mult in atr_values:

        for trailing_mult in trailing_values:

            trades, equity_curve, final_capital = run_backtest(
                data,
                initial_capital=initial_capital,
                atr_multiplier=atr_mult,
                trailing_atr_multiplier=trailing_mult
            )

            metrics = calculate_performance(
                trades=trades,
                equity_curve=equity_curve,
                initial_capital=initial_capital,
                final_capital=final_capital
            )

            results.append({
                "atr_multiplier": atr_mult,
                "trailing_multiplier": trailing_mult,
                "final_capital": metrics["final_capital"],
                "return_%": metrics["total_return_%"],
                "max_drawdown_%": metrics["max_drawdown_%"],
                "profit_factor": metrics["profit_factor"],
                "win_rate_%": metrics["win_rate_%"]
            })

    results_df = pd.DataFrame(results)

    results_df = results_df.sort_values(
            by="return_%",
            ascending=False
    ).reset_index(drop=True)

    return results_df