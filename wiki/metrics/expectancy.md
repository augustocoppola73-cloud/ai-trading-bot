# Expectancy

Expectancy is not currently implemented as a first-class metric.

## Concept

Expectancy estimates average expected profit or loss per trade:

```text
expectancy = (win_rate * average_win) - (loss_rate * average_loss)
```

## Why It Matters

Expectancy can reveal whether a strategy has positive average value even when
win rate alone looks misleading.

## Future Implementation Notes

If added, compute it from closed trades and document whether it uses percentage
returns, currency PnL, or risk units.
