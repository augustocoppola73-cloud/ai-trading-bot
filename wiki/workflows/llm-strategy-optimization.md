# LLM Strategy Optimization Workflow

End-to-end loop for refining strategy parameters using an external LLM.

## Steps

1. **Run backtest** — Select a strategy preset and market, then run the
   portfolio backtest from the dashboard sidebar.
2. **Generate prompt** — In the backtest results "Prompt per analisi LLM" tab,
   generate a full-context prompt containing strategy config, performance
   metrics, and per-ticker stats.
3. **Send to LLM** — Copy the prompt (or download the `.txt`) and paste it into
   ChatGPT, Claude, Gemini, or any other LLM.
4. **Receive optimized JSON** — The LLM responds with a complete, ready-to-import
   JSON file containing all 30 strategy parameters (the prompt explicitly
   requests this format).
5. **Save as JSON file** — Copy the LLM's JSON block into a `.json` file.
   The output is designed to be valid JSON with no placeholders or comments.
6. **Import into dashboard** — Use the "Importa strategia da JSON" section in
   the sidebar:
   - Upload the `.json` file.
   - Optionally provide a custom name (defaults to "Importato YYYY-MM-DD HH:MM").
   - Click "Importa e salva".
7. **Re-run backtest** — Select the imported preset and backtest it to compare
   against the original.

## Prompt Structure

The generated prompt (`prompt_generator.py`) includes:

- Context on the strategy type (momentum/trend-following with weekly rotation).
- Full list of current parameter values.
- Backtest results as structured JSON (metrics, per-ticker stats, return
  distribution, rotation reasons).
- A 4-step task for the LLM:
  1. **Diagnosi** — identify performance issues.
  2. **Configurazione ottimizzata** — produce a complete JSON with all 30
     parameters, ready to save as `.json` and import directly.
  3. **Spiegazione** — justify each changed parameter.
  4. **Avvertenze** — flag overfitting risk per change.

The prompt asks the LLM to fill in every parameter (including unchanged ones)
so the JSON output is self-contained and does not require manual editing.

## JSON Format

The importer accepts:

- A flat dictionary with all 30 strategy parameters:
  ```json
  {
    "ma_type": "EMA",
    "fast_ma_period": 8,
    "slow_ma_period": 21,
    "long_ma_period": 50,
    "rsi_period": 14,
    "rsi_buy_min": 30,
    "rsi_buy_max": 70,
    "rsi_sell_above": 80,
    "atr_period": 14,
    "max_volatility_pct": 5.0,
    "adx_period": 14,
    "adx_min": 20,
    "use_adx_filter": true,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "use_macd_filter": false,
    "volume_sma_period": 20,
    "volume_ratio_min": 1.0,
    "use_volume_filter": false,
    "min_ai_score": 50,
    "min_scanner_score": 0.4,
    "min_hold_weeks": 2,
    "persistence_weeks": 3,
    "switch_score_margin": 15,
    "top_n_candidates": 5,
    "commission_pct": 0.1,
    "slippage_pct": 0.05,
    "use_engine_basket": false,
    "engine_basket_size": 5
  }
  ```
- A wrapped object with a recognized key (`configurazione_strategia`,
  `strategy_config`, `params`, `parameters`) containing the parameter dict.

Only keys that match valid strategy parameters are imported. Missing keys are
filled from the currently active preset, so partial JSON is accepted.

## Validation

- Invalid JSON → error shown, nothing saved.
- No recognized parameter keys → error with guidance on expected keys.
- Partial match → merged with current preset; success message shows how many
  keys were imported vs total.

## Iteration

Repeat the loop: backtest the imported preset, generate a new prompt with the
updated results, and refine further with the LLM.
