# Performance Rules

Optimize only when a bottleneck is identified.

Current likely performance sensitivities:

- Repeated yfinance downloads.
- Scanning large market universes.
- Recomputing indicators per ticker.
- Running historical scans inside dashboard interactions.

Current backtest optimization direction:

- Load raw daily prices through bulk SQLite reads and bulk yfinance downloads
  for missing or stale tickers only.
- Keep the active backtest universe in Streamlit session memory and reuse it
  across repeated runs of the same universe.
- Keep indicator, AI score, and signal preparation preset-specific because
  presets can change their parameters.
- Precompute weekly rebalance scanner snapshots instead of repeatedly filtering
  every ticker DataFrame for every rebalance date.
- Reuse prepared primary-preset data for engine basket selection instead of
  running a duplicate historical scan over the full universe.
- Report progress by meaningful phases so ETA does not reach zero while a
  heavy phase is still active.
- Prefer vectorized Pandas operations for row-independent scoring logic.
- Preserve existing portfolio history columns and trading behavior when
  optimizing.

Prefer profiling and measurement before changing architecture.

Readability and reproducibility are higher priority than micro-optimization.
