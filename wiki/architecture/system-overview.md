# System Overview

AI Trading Bot is a Streamlit-based trading research dashboard. It combines
market universe discovery, historical market data, technical indicators, simple
AI-style scoring, signal generation, backtesting, paper portfolio planning, and
interactive visualization.

## Current Runtime Shape

The system is organized as functional Python modules under `src/`.
The dashboard imports those modules directly and acts as the user-facing
orchestration layer.

Core responsibilities:

- Data acquisition: `market_data.py`, `market_universe.py`.
- Feature engineering: `indicators.py`, `ai_filter.py`.
- Signal and score generation: `strategy.py`, `portfolio_scanner.py`.
- Backtesting and simulation: `backtest.py`, `basket_backtest.py`,
  `portfolio_backtest.py`.
- Risk and allocation: `risk_manager.py`, `portfolio_engine.py`.
- Metrics: `performance.py`, `portfolio_performance.py`.
- UI and visualization: `dashboard.py`.
- Generated outputs: `reports/*.csv`.

## Architectural Intent

The intended architecture should keep business logic separate from UI rendering.
At present, `dashboard.py` performs substantial orchestration, which is practical
for a small Streamlit project but should be watched as the system grows.

Future evolution should preserve:

- Explicit Pandas transformations.
- Small, readable functions.
- Reproducible portfolio histories.
- Clear separation between analysis logic and visualization.
