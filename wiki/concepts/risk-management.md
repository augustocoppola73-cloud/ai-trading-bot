# Risk Management

Risk management currently centers on position sizing and volatility filtering.

## Position Sizing

`risk_manager.calculate_position_size_by_risk` calculates allocation from:

- Available capital.
- Entry price.
- Stop loss price.
- Risk per trade.

The allocation is capped at available capital.

## Volatility Filtering

Scanner and portfolio logic use ATR relative to close price as a volatility
measure. Dynamic portfolio candidates can be rejected when `volatility_%`
exceeds the configured maximum.

## Guiding Principle

Risk logic must remain explicit and inspectable. Avoid hidden fallback behavior
or opaque allocation rules.
