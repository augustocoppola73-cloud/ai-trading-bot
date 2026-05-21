# Drawdown

Drawdown measures the decline from a previous portfolio peak.

The project calculates drawdown by:

1. Computing cumulative peak equity or capital.
2. Comparing current value to that peak.
3. Expressing the result as a percentage.

Formula:

```text
drawdown_% = (current_value - peak_value) / peak_value * 100
```

Max drawdown is the minimum drawdown value in the series.

Drawdown should remain negative or zero. A less negative max drawdown indicates
smaller peak-to-trough loss.
