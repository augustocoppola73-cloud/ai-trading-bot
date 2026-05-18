# Portfolio Engine

The project currently has two related portfolio concepts:

## Paper Portfolio Plan

`portfolio_engine.build_portfolio_plan` turns scanner results into a proposed
portfolio allocation.

It:

- Filters for high scanner score.
- Requires BULL market regime.
- Requires BUY signal.
- Selects the top candidates.
- Calculates stop loss and initial trailing stop.
- Uses `risk_manager.calculate_position_size_by_risk`.
- Returns a portfolio plan DataFrame and remaining cash.

## Dynamic Portfolio Backtest

`portfolio_backtest.run_portfolio_backtest` simulates weekly rotation across a
market universe.

It:

- Loads raw market prices separately from preset-specific preparation.
- Reuses raw market prices across dashboard multi-preset comparisons.
- Applies indicators, AI score, and signals per preset.
- Precomputes weekly scanner snapshots before simulation.
- Filters candidates by signal, regime, score, and volatility.
- Tracks candidate persistence.
- Enforces minimum holding weeks.
- Allows forced rotation when the current asset weakens.
- Applies commission and slippage to weekly returns.
- Emits a portfolio history DataFrame.

## Design Constraint

Portfolio logic should stay independent from Streamlit. The dashboard may call
portfolio functions, but portfolio state transitions should remain testable
without UI.
