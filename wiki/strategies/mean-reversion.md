# Mean Reversion

Mean reversion is not currently implemented as a primary strategy.

## Concept

Mean reversion strategies assume that stretched prices may move back toward a
normal range.

Potential inputs:

- RSI extremes.
- Distance from moving averages.
- Bollinger-style bands.
- Volatility regime.

## Governance

Do not mix mean reversion rules into the current momentum strategy without
documenting the decision. A separate strategy function or mode is preferable
when behavior diverges meaningfully.
