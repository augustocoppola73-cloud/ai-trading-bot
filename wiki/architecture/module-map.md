# Module Map

## Data Sources

- `market_data.py`: downloads historical market data through yfinance,
  normalizes column names, and uses the local SQLite price cache for daily
  data.
- `market_universe.py`: builds progressive multi-market universes from Nasdaq
  Trader directories, CoinGecko, local Italy/Europe seed catalogs, overrides,
  and verified custom tickers.
- `market_cache.py`: stores universe records, yfinance daily prices, verified
  symbols, and provider errors in `reports/market_data_cache.sqlite`.

## Feature And Signal Pipeline

- `indicators.py`: adds EMA, RSI, ATR, uptrend, and market regime.
- `ai_filter.py`: adds a deterministic `ai_score` based on trend, RSI, and volatility.
- `strategy.py`: generates BUY, SELL, HOLD signals.
- `portfolio_scanner.py`: computes scanner scores and ranks current opportunities.
- `historical_scanner.py`: scans opportunities as of a historical date.

## Backtesting And Portfolio Logic

- `backtest.py`: single-asset trade simulation with stops and trailing stops.
- `basket_backtest.py`: equally weighted buy-and-hold static basket benchmark.
- `portfolio_backtest.py`: dynamic weekly portfolio rotation engine.
- `portfolio_engine.py`: paper portfolio construction and position sizing.
- `risk_manager.py`: risk-based position sizing helper.

## Metrics And Comparison

- `performance.py`: single-asset performance and drawdown calculations.
- `portfolio_performance.py`: portfolio history metrics.
- `benchmark.py`: buy-and-hold benchmark metrics.
- `optimizer.py`: simple parameter grid search over stop settings.
- `ai_strategy_advisor.py`: LLM-based post-backtest strategy analysis and
  parameter suggestions (advisory only).

## UI And Reports

- `dashboard.py`: Streamlit dashboard, parameter collection, orchestration,
  Plotly charts. Includes an "Esegui Scanner Live" button that triggers
  `paper_trading.run_paper_trading_for_tickers` with the active preset and
  selected markets.
- `paper_trading.py`: writes live scanner and paper trading CSV reports.
  Accepts `strategy_config` to propagate the active preset through the
  pipeline. Exposes `run_paper_trading_for_tickers` for dashboard use and
  `run_paper_trading_for_market` for single-market runs.
- `run_paper_trading.py`: CLI entry point for daily paper trading. Uses
  `--market` to select from the universe catalog (default: Italy - Borsa
  Italiana). Supports `--capital`, `--top-n`, `--min-score` arguments.
