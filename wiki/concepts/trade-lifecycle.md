# Trade Lifecycle

The single-asset backtest lifecycle is:

1. Start with cash and no position.
2. Enter when signal is BUY and there is no open position.
3. Size the position based on stop-loss distance and risk per trade.
4. Track highest price since entry.
5. Update trailing stop when price makes a new high.
6. Exit on active stop or SELL signal.
7. Record trade event and update cash.

The dynamic portfolio lifecycle is different: it models weekly rotation between
one selected asset and CASH rather than detailed intra-position stop handling.
