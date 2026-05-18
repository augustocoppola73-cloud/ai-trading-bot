# Dashboard Architecture

The dashboard is implemented in `src/dashboard.py` using Streamlit.

## Responsibilities

The dashboard is now organized as a Streamlit workstation rather than a
linear report page. It currently:

- Defines page configuration and page title.
- Loads one or more selected market universes with graceful failure handling
  when a public provider is unavailable or rate-limited. The scanner defaults
  to all successfully loaded markets so the user does not see only the first
  available universe.
- Organizes markets by group: USA, ETF, Italy, Europe, Crypto, and Custom, with
  quick universe presets for global progressive, USA, ETF, Italy, Europe Core,
  Crypto, and custom views.
- Keeps compact workspace controls in the sidebar.
- Keeps quick asset search visible in the sidebar, while advanced basket and
  strategy controls stay collapsed until needed.
- Shows a watchlist built from manual basket tickers, latest scanner output,
  latest paper portfolio tickers, and user-starred
  favorites persisted in `reports/watchlist.json`.
- Provides a guided Trova asset view with health metrics, compact filters,
  a single screener table, watchlist checkbox, scanner metrics, technical
  columns, and optional price charts with common finance time ranges.
- Shows operational scanner fields from the latest available daily close,
  including setup score, opportunity label, reason, last close date, Bollinger
  context, and filters for long candidates or sell/exit signals.
- Keeps global asset search separate from the active-market screener. Global
  search can find assets outside the current filters and send them directly to
  watchlist, asset focus, or manual basket.
- Renders global asset search in two UI modes: compact vertical controls for
  sidebar basket/watchlist actions, and full-width detail controls in Market
  Scanner.
- Allows manual ticker validation through yfinance; valid symbols are persisted
  as `Custom / Verified` metadata in the local SQLite cache.
- Groups the experience into Overview, Trova asset, Portfolio, Testa strategia,
  and Glossario & Strategia tabs.
- Keeps the Overview chart full-width, with watchlist and asset focus below it
  so metrics remain readable when the sidebar is open.
- Keeps asset focus persistent through filter and time-range changes; the
  asset chart renders automatically when a focus ticker is selected.
- Supports trading-board style asset focus charts with separate visible range
  and candle interval controls, line/candlestick rendering, volume subpanel,
  current-price line, OHLC summary, optional trend moving average, and
  Bollinger overlays.
- Provides two chart engines in asset focus: a KLineCharts-based
  "Trading board pro" beta for professional manual analysis, and a Plotly
  fallback for local reliability.
- Keeps professional drawing tools inside the chart component rather than
  Streamlit widgets so switching between segment, ray, price line, channel,
  Fibonacci, ruler, and erase does not trigger a Streamlit rerun.
- Uses fallback price ranges for asset charts when a provider has no data for
  the requested short interval, while keeping the selected focus visible.
- Keeps glossary and strategy content in the dedicated tab rather than the
  sidebar.
- Keeps asset focus optional so the table remains the primary view
  until a ticker is selected for detail.
- Runs dynamic portfolio backtests on the combined active-market universe,
  including multi-preset comparison curves from editable strategy presets
  persisted in `reports/backtest_presets.json`.
- Defaults backtest end date to today and start date to the last year, with
  quick range presets for 1W, 2W, 1M, 3M, last quarter, 6M, and 1Y.
- Shows dynamic backtest progress with current phase, preset, ticker/week
  counts, cache/download counts, elapsed time, and estimated remaining time.
- Uses `reports/market_data_cache.sqlite` for daily price caching so large
  universes can be revisited without redownloading every ticker.
- Keeps the active backtest universe's raw price data in Streamlit session
  memory and reuses it for repeated runs while the universe/freshness key is
  unchanged.
- Presents six protected base strategy presets ordered from defensive to
  aggressive plus an ETF-focused dual-SMA profile, with custom preset creation
  for advanced users.
- Supports importing strategy presets from JSON files (e.g. LLM-optimized
  configurations) with automatic parameter validation, nested key extraction,
  and merge with current preset defaults for missing keys.
- Runs manual static basket benchmarks from assets selected through global
  search, quick ticker entry, or existing watchlist/context.
- Runs engine-selected static basket benchmarks from the selected market.
- Calculates metrics.
- Renders Plotly equity curves, benchmark comparisons, and asset charts.
- Shows generated CSV and JSON report tables and audit references.
- Provides CSV download buttons.

## Visualization Pattern

Plotly `go.Figure` objects are used directly. Existing chart types include:

- Equity curve line charts.
- Dynamic portfolio versus benchmark comparison.
- Portfolio rotation timeline with custom hover data.
- Single asset focus chart loaded on demand. The pro beta uses KLineCharts
  through `components.html` with OHLCV data passed from Python. Plotly remains
  available as a fallback chart engine.

## Architectural Watch Point

`dashboard.py` is both UI and orchestration. This is acceptable at the current
scale, but future growth may justify moving orchestration into service-style
functions while keeping Streamlit focused on rendering and user input.

Static explanatory dashboard content lives in `dashboard_content.py` so glossary
and strategy descriptions remain visible without changing trading logic.

The workstation redesign is a UI restructuring only. It must not change signal
rules, scanner scoring, backtest logic, or portfolio sizing.

Professional manual Fibonacci retracement, ruler measurement, and low-latency
drawing interactions are handled by the pro chart component rather than Plotly.
Persistent drawings are still a future integration point because Streamlit's
static HTML component does not automatically round-trip chart overlay state
back to Python.
