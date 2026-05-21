# PnL Calculation

PnL means profit and loss.

## Single-Asset Backtest

`backtest.py` calculates trade PnL on exits:

```text
pnl_% = (exit_price - entry_price) / entry_price * 100
```

Exit events include SELL, STOP_LOSS, and TRAILING_STOP.

## Dynamic Portfolio Backtest

`portfolio_backtest.py` calculates weekly gross return, then subtracts two-sided
commission:

```text
gross_return = (exit_price - entry_price) / entry_price
net_return = gross_return - (commission_pct * 2)
capital = capital * (1 + net_return)
```

Slippage is applied by increasing entry price and reducing exit price.
