# Data Flow

The dominant data flow is DataFrame-oriented.

## Market Backtest Flow

1. `market_universe.get_assets_for_market` returns ticker lists from the
   selected progressive market catalog.
1. `market_universe.get_asset_records_for_market_with_status` returns enriched
   asset records with group, market, ticker, name, type, exchange, currency,
   source, and success/error status for UI-safe loading.
1. `market_universe.get_all_market_asset_records_with_status` combines Nasdaq
   listed, other-listed, ETF, Italy, Europe Core, Crypto, overrides, and
   verified custom tickers. Provider errors are recorded so the dashboard can
   degrade gracefully.
1. `dashboard.py` uses the complete catalog for global asset search while the
   screener table remains filtered by active markets. Search results can update
   watchlist, persistent asset focus, or the manual benchmark basket without
   changing active-market filters.
2. `portfolio_backtest.load_market_price_data` loads raw OHLCV data for the
   requested backtest universe.
3. `market_cache.load_price_data_bulk` reads cached daily OHLCV rows for the
   full universe in SQLite chunks and marks tickers as loaded, missing, stale,
   or invalid.
4. `market_data.download_data_bulk` requests only missing or stale tickers from
   yfinance in batches, then stores successful downloads back to SQLite.
5. `dashboard.py` keeps the loaded raw prices in Streamlit session state and
   reuses them across repeated runs of the same active universe.
6. `portfolio_backtest.prepare_strategy_market_data` applies the active preset:
   `indicators.add_indicators`, `ai_filter.calculate_ai_score`, and
   `strategy.generate_signals`.
7. `portfolio_backtest.build_rebalance_scanners` precomputes scanner snapshots
   for weekly rebalance dates using the latest available ticker row at or before
   each scan date.
8. `portfolio_backtest.run_portfolio_backtest` filters candidates and selects
   CASH or one active ticker.
9. The engine basket benchmark reuses the prepared primary-preset market data
   instead of running a second historical scan over the full universe.
10. `portfolio_performance.calculate_portfolio_performance` calculates portfolio metrics.
11. `dashboard.py` renders metrics, equity curves, timelines, tables, and downloads.

## Paper Trading Flow

1. `portfolio_scanner.scan_market` scans current ticker data using the active
   `strategy_config` for indicators, AI score, and signals.
2. `portfolio_engine.build_portfolio_plan` filters candidates, records decision
   reasons, and sizes positions.
3. `paper_trading.run_daily_paper_trading` accepts `strategy_config` and writes
   scanner, plan, summary, decision log, run manifest, and universe snapshot
   files.
4. `paper_trading.run_paper_trading_for_tickers` is a convenience wrapper used
   by the dashboard to scan an arbitrary ticker list with a market label and
   strategy config.
5. `dashboard.py` provides an "Esegui Scanner Live" button in the scanner tab
   that runs the full paper trading pipeline on the active-market tickers
   (optionally limited to cached assets) using the current preset. After
   completion it reloads report data via `st.rerun()`.
6. `dashboard.py` also reads latest paper trading artifacts from `reports/` and
   shows the live plan, audit files, and comparison with the previous run.

## Data Contracts To Preserve

Universe records include:

- `group`
- `market`
- `ticker`
- `name`
- `asset_type`
- `exchange`
- `currency`
- `source`

Local catalog inputs include:

- `reports/market_catalog_italy.csv`
- `reports/market_catalog_europe_core.csv`
- `reports/market_catalog_overrides.csv`

Verified custom ticker metadata is stored in
`reports/market_data_cache.sqlite`.

Portfolio history currently expects columns such as:

- `scan_date`
- `ticker`
- `reason`
- `weeks_held`
- `entry_price`
- `exit_price`
- `weekly_return_%`
- `capital`
- `gross_return_%`
- `net_return_%`
- `scanner_score`
- `volatility_%`

Metric and visualization code depend on these names.

Paper trading reports currently include:

- `reports/live_scanner_YYYY-MM-DD.csv`
- `reports/paper_portfolio_plan_YYYY-MM-DD.csv`
- `reports/paper_summary_YYYY-MM-DD.csv`
- `reports/paper_decision_log_YYYY-MM-DD.csv`
- `reports/run_manifest_YYYY-MM-DD.json`
- `reports/universe_snapshot_<market>_YYYY-MM-DD.csv`

Paper portfolio plan rows include audit columns such as `position_status`,
`decision_reason`, `risk_$`, and `risk_%`. Summary rows include `run_id`,
`market`, `cash_%`, `exposure_%`, key parameters, and generated file paths.
