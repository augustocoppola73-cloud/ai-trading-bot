# Backtesting

Backtesting simulates how a strategy would have behaved over historical data.

## Current Backtest Types

- Single-asset backtest: detailed trade lifecycle with stops and trailing stops.
- Dynamic portfolio backtest: weekly rotation across a ticker universe.
- Static basket backtest: equal-weight buy-and-hold benchmark.
- Multi-preset portfolio comparison: repeated dynamic backtests over the same
  active universe using different strategy parameter presets.

## Known Assumptions

- Market data comes from yfinance.
- Daily market data is cached locally in SQLite at
  `reports/market_data_cache.sqlite`.
- Dynamic portfolio rebalances weekly on Monday dates.
- Dynamic portfolio applies configurable slippage and commission.
- Dynamic portfolio backtests separate raw price loading from per-preset
  indicator and signal preparation. Dashboard multi-preset comparisons load
  raw prices once and reuse them across preset runs.
- Large-universe price loading uses bulk SQLite reads first, then bulk
  yfinance downloads only for missing or stale tickers. During a Streamlit
  session, the dashboard keeps the active backtest universe in memory and
  reuses it when the same universe is run again.
- Weekly dynamic portfolio scans use precomputed rebalance snapshots that keep
  the same rule as the original scan: use the latest available row at or before
  each rebalance date.
- Strategy presets can configure trend, RSI, ATR, ADX, MACD, volume, scoring,
  persistence, and execution assumptions.
- The dashboard exposes five protected base presets ordered by aggressiveness:
  Defensive Trend, Conservative Rotation, Balanced Rotation, Growth Momentum,
  and Aggressive Breakout. User presets are saved separately as custom JSON.
- Static basket uses equal initial allocation and forward-filled asset values.
- Large-universe backtests can use all selected assets or only assets already
  present in cache to reduce provider load.
- The dashboard shows progress while dynamic portfolio backtests run. Progress
  is estimated from selected presets, ticker count, weekly rebalance dates, and
  optional benchmark steps.
- Progress distinguishes cache reads, provider downloads, preset preparation,
  simulation, and benchmark phases. ETA is advisory and should not show zero
  while a non-completed phase is still running.
- Assets with unavailable prices or invalid prepared indicators are excluded
  from the run and counted in progress/status messaging.
- ETA is advisory because provider latency and cache hits can vary between
  assets and runs.

Backtests are research tools, not guarantees of live trading performance.
