# ETF Dual SMA RSI

## Intent

This preset captures broad, liquid ETF trends with simple deterministic rules.
It is inspired by the dual moving-average crossover pattern with an RSI
momentum filter, but it runs inside the existing project engine rather than as
a separate trading bot.

The goal is not to predict breakouts. The strategy waits for a confirmed trend
and avoids entries when momentum is already overextended.

## Inputs

Required columns and indicators:

- Daily OHLCV data.
- `trend_fast_ma`: 20-day SMA.
- `trend_slow_ma`: 50-day SMA.
- `trend_long_ma`: 200-day SMA.
- 14-day RSI.
- 14-day ATR.
- Deterministic `ai_score`.
- `market_regime`.

Recommended universe:

- Highly liquid ETFs such as broad-market or sector ETFs.
- Avoid thin instruments where spreads and provider gaps can distort signals.

## Entry Logic

BUY requires:

- 20-day SMA above 50-day SMA.
- Close above 200-day SMA.
- RSI between 40 and 65.
- `ai_score` at or above 70.
- BULL market regime.
- ATR volatility no higher than 4.5%.

The project does not currently model an exact crossover event as a separate
condition. It uses the current fast-above-slow state, then lets persistence,
minimum hold, scanner score, and rotation rules reduce churn.

## Exit Logic

SELL occurs when:

- 20-day SMA falls below 50-day SMA.
- Or RSI rises above 70.

Backtests and paper plans also use the existing engine stop logic. Current
single-asset backtests use ATR-based stop-loss and trailing-stop behavior;
portfolio rotation exits can also occur when a stronger candidate replaces the
current holding.

## Risk Rules

The preset keeps risk conservative by using:

- SMA rather than EMA to reduce sensitivity.
- RSI maximum of 65 for new BUY setups.
- Moderate ATR volatility ceiling.
- Three top candidates and a three-asset engine basket.
- Commission and slippage set to 0.08% each.

The article that inspired this preset mentions a fixed 5% stop and maximum 2%
portfolio allocation per trade. Those controls are not encoded in this preset
because the current engine centralizes sizing in `risk_manager.py` and stop
behavior in the backtest/portfolio modules. Add those as explicit engine
features before relying on them operationally.

## Metrics To Watch

- Max drawdown.
- Sharpe ratio.
- Expectancy.
- Win rate.
- Turnover and number of weeks in cash.
- Difference between ETF basket benchmark and dynamic rotation result.

## Failure Modes

This strategy can perform poorly during:

- Sideways markets with repeated SMA whipsaws.
- Fast V-shaped reversals where SMA confirmation arrives late.
- High-volatility selloffs where daily closes gap below intended stops.
- ETF universes with low liquidity or stale data.
