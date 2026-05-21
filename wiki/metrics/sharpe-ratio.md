# Sharpe Ratio

Sharpe ratio is not currently implemented as a core metric.

## Concept

Sharpe ratio estimates risk-adjusted return:

```text
Sharpe = (average_return - risk_free_rate) / return_standard_deviation
```

## Future Implementation Notes

If added, define:

- Return frequency.
- Annualization factor.
- Risk-free rate assumption.
- Whether returns come from daily equity or weekly portfolio history.

Do not add Sharpe ratio without making these assumptions explicit.
