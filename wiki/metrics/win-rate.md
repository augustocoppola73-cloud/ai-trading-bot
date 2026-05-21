# Win Rate

Win rate measures how often outcomes are positive.

## Single-Asset

`performance.calculate_performance` calculates win rate over closed trades:

- SELL
- STOP_LOSS
- TRAILING_STOP

## Portfolio

`portfolio_performance.calculate_portfolio_performance` calculates weekly win
rate from `weekly_return_%` when available, otherwise from capital changes.

## Caution

High win rate does not imply good expectancy. Small frequent wins can still be
outweighed by large losses.
