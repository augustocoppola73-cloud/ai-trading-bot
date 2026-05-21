# AI-Assisted Signals

The current `ai_score` is deterministic and rule-based. It is not an external
LLM or machine learning model.

## Current Inputs

The score considers:

- EMA trend alignment.
- Price above long-term moving average.
- RSI range.
- ATR relative to close price.

## Design Principle

AI-assisted signals should remain explainable. If model-based scoring is added,
store:

- Input features.
- Training data assumptions.
- Evaluation method.
- Failure modes.
- Whether the model affects live decisions or only advisory insights.
