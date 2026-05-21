# Portfolio Dashboard

The dashboard currently has two modes:

## Dynamic Backtest Mode

Triggered by the sidebar button. It runs a fresh market portfolio backtest and
optional benchmark baskets, then renders:

- Summary metrics.
- Benchmark table.
- Equity comparison chart.
- Portfolio timeline.
- Portfolio history table.
- Benchmark history tables.
- CSV downloads.

## Default Report Mode

When no fresh backtest is run, it reads generated CSV files from `reports/` and
shows:

- Single-asset final capital.
- Multi-asset final capital.
- Equity curve comparison.
- Trades table.
- Portfolio backtest table.
- Latest paper trading plan and summary when present.
