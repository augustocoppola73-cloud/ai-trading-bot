# Market Catalog

The dashboard separates the global market catalog from active scanner filters.

## Global Catalog

The global catalog is the complete set of loaded asset records from public
directories, local seed files, user overrides, and verified custom tickers.
Global search uses this full catalog so a user can find assets such as `BYSI`
even when the active scanner market is Italy.

## Active Markets

Active markets are the subset selected in the dashboard sidebar. They control
which assets appear in the main screener table and which universe is used for
default backtest runs.

## Local Seeds

Editable CSV files extend markets that do not currently have a robust public
directory integration:

- `reports/market_catalog_italy.csv`
- `reports/market_catalog_europe_core.csv`

These files should use yfinance-compatible tickers such as `TIP.MI`.

## Overrides And Custom Verified

`reports/market_catalog_overrides.csv` is for explicit user corrections or
manual additions. Tickers validated from the dashboard are stored as
`Custom / Verified` metadata in the SQLite cache.
