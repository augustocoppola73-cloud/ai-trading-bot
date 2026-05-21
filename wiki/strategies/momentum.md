# Configurable Momentum Rotation

The current strategy is a configurable trend-following and momentum rotation
model. It can be run through protected base presets or custom user presets.

## Current Signals

BUY requires:

- Fast moving average above slow moving average.
- Close above the long moving average.
- RSI inside the preset buy range.
- AI score above the preset threshold.
- BULL market regime.
- ATR volatility below the preset maximum.
- Optional ADX, MACD, and volume confirmations when enabled.

SELL occurs when:

- Fast moving average falls below slow moving average.
- Or RSI rises above the preset sell threshold.

## Preset Ladder

- `1 - Defensive Trend`: slow filters, low volatility, ADX/MACD/volume required.
- `2 - Conservative Rotation`: stable trend confirmation with moderate rotation.
- `3 - Balanced Rotation`: central profile close to the original engine.
- `4 - Growth Momentum`: faster trend capture with more rotations.
- `5 - Aggressive Breakout`: permissive and responsive breakout profile.
- `6 - ETF Dual SMA RSI`: simple ETF-oriented SMA 20/50 profile with a
  conservative RSI 40-65 entry window.

## Parameters

The configurable parameter groups are trend averages, RSI, ATR volatility,
ADX, MACD, volume ratio, AI score, scanner score, persistence, rotation margin,
candidate count, commission, and slippage.

## Operational Scanner Context

The scanner keeps the primary momentum/trend-following signal rules intact, but
adds operational context for today's review. It evaluates the latest available
daily close for each ticker and exposes setup score, opportunity label, reason,
last close date, and Bollinger band position. Bollinger data is a ranking and
explanation input, not a separate primary entry strategy.

## Risk

Momentum strategies can underperform during sideways markets, sudden reversals,
or high-volatility whipsaws. More aggressive presets increase turnover and
potential drawdown.
