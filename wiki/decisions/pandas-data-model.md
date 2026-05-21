# Pandas Data Model

## Decision

Use Pandas DataFrames as the primary in-memory data model.

## Rationale

The project is centered on time series, scanner tables, portfolio history, and
CSV report artifacts. Pandas keeps these flows explicit and inspectable.

## Current Contracts

Important DataFrame contracts include:

- Market data with normalized lowercase columns.
- Indicator-enriched data with `ema_20`, `ema_50`, `ema_200`, trend moving
  averages, `rsi`, `atr`, ADX, MACD, volume ratio, Bollinger bands,
  `market_regime`, and `signal`.
- Scanner output with ticker, close, ATR, volatility, score, AI score, regime,
  signal, RSI, latest close date, setup score, opportunity label, reason, and
  Bollinger context.
- Portfolio history with scan date, selected ticker, reason, returns, capital,
  scanner score, and volatility.

## Risk

Column-name coupling is strong. Any column rename should be treated as an
interface change and coordinated across metrics, dashboard, reports, and tests.
