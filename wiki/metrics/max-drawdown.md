# Max Drawdown

Max drawdown is implemented in both single-asset and portfolio performance code.

## Single-Asset

`performance.calculate_drawdown` uses the `equity` column.

## Portfolio

`portfolio_performance.calculate_portfolio_performance` uses the `capital`
column.

## Interpretation

The result is a percentage, usually negative. Example:

```text
-18.5 means the portfolio declined 18.5% from a previous peak.
```

Max drawdown should be treated as a core risk metric, not merely a performance
summary.
