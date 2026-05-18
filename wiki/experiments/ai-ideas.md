# AI Ideas

AI should assist the system, not obscure it.

Potential AI-assisted capabilities:

- Explain why a scanner result ranked highly.
- Summarize portfolio rotation decisions.
- Generate research notes from backtest results.
- Suggest hypotheses for strategy experiments.
- Detect unusual changes in generated reports.

## Implemented: AI Strategy Advisor (post-backtest)

Module: `src/ai_strategy_advisor.py`

After running a portfolio backtest, the AI Advisor tab in the dashboard allows
the user to send backtest results to an LLM for analysis. The advisor:

- Receives: strategy parameters, portfolio metrics, per-ticker performance,
  rotation reasons, cash ratio.
- Returns: diagnosis of weak points, concrete parameter suggestions (with
  current vs suggested values), overfitting warnings.
- Is purely advisory — no automatic changes are applied.
- Requires `OPENAI_API_KEY` in a `.env` file and the `openai` package.

Governance rule: AI-generated insight should be advisory unless explicitly
promoted into deterministic, reviewed business logic.
