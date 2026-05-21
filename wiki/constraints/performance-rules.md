# Performance Rules

Optimize only when a bottleneck is identified.

Current likely performance sensitivities:

- Repeated yfinance downloads.
- Scanning large market universes.
- Recomputing indicators per ticker.
- Running historical scans inside dashboard interactions.
- Running live scanner downloads ticker-by-ticker when a bulk/cache path exists.

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

Live market scanner optimization direction:

- Prefer the same bulk SQLite read and bulk yfinance download path used by
  portfolio backtests.
- Refresh stale daily prices incrementally when cached history already exists:
  use an overlap window from the cached `last_date` and upsert downloaded rows
  into the price cache instead of deleting and rewriting the full ticker
  history.
- Keep full-period provider downloads for missing or invalid ticker histories.
- Treat cache-only actions as strict no-provider operations. If the user asks
  for cached assets only, stale or missing tickers must not trigger yfinance
  downloads during that interaction.
- Use a tolerant daily freshness window so weekends and market holidays do not
  mark thousands of tickers stale at once.
- Keep filter changes in the dashboard as dataframe operations over existing
  scanner reports; changing screener filters must not trigger fresh provider
  downloads.
- Keep screener filter logic in pure, testable functions rather than inside
  Streamlit callbacks.

Prefer profiling and measurement before changing architecture.

Readability and reproducibility are higher priority than micro-optimization.
