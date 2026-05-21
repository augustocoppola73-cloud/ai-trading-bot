# Portfolio Performance

Portfolio performance is calculated from portfolio history.

Current outputs:

- `initial_capital`
- `final_capital`
- `total_return_%`
- `max_drawdown_%`
- `weekly_win_rate_%`
- `best_week_%`
- `worst_week_%`

## Inputs

`calculate_portfolio_performance` expects:

- A portfolio history DataFrame.
- Initial capital.
- Final capital.

If history is missing or does not contain `capital`, the function returns a
minimal metric set with drawdown and weekly statistics set to zero.

## Evolution Note

Future metrics should avoid silently changing this contract because the
dashboard and benchmark tables depend on these keys.
