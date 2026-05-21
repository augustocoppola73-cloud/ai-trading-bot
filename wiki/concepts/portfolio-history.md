# Portfolio History

Portfolio history is the persistent record of simulated portfolio state over
time.

In the dynamic backtest, each row represents a weekly decision window. Rows can
represent either an active ticker or CASH.

Current fields include:

- `scan_date`: rebalance decision date.
- `ticker`: selected asset or CASH.
- `reason`: why the position was held, changed, or moved to cash.
- `weeks_held`: holding duration for the selected asset.
- `entry_price` and `exit_price`: weekly simulated prices after slippage.
- `weekly_return_%`: net weekly return after commission and slippage.
- `capital`: portfolio value after the period.
- `scanner_score` and `volatility_%`: selection context.

This object is central because metrics, charts, and downloads depend on it.
