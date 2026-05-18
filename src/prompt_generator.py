"""Prompt Generator — builds a ready-to-paste LLM prompt from backtest results.

Generates a structured JSON payload and a detailed Italian prompt
for manual analysis with any LLM (ChatGPT, Claude, Gemini, etc.).
"""

import json

import pandas as pd


def build_backtest_payload(
    portfolio_history: pd.DataFrame,
    portfolio_metrics: dict,
    strategy_config: dict,
    market_label: str = ""
) -> dict:
    """Build a structured JSON payload from backtest results."""

    payload = {
        "mercato": market_label,
        "configurazione_strategia": _format_strategy_config(strategy_config),
        "metriche_performance": _format_metrics(portfolio_metrics),
    }

    if portfolio_history is not None and not portfolio_history.empty:
        history = portfolio_history.copy()
        payload["settimane_totali"] = len(history)

        if "ticker" in history.columns:
            cash_weeks = int((history["ticker"] == "CASH").sum())
            active_weeks = len(history) - cash_weeks
            payload["settimane_cash"] = cash_weeks
            payload["settimane_attive"] = active_weeks

            active = history[history["ticker"] != "CASH"]

            if not active.empty and "ticker" in active.columns:
                ticker_stats = _compute_ticker_stats(active)
                payload["performance_per_ticker"] = ticker_stats

            if "weekly_return_%" in history.columns:
                returns = history["weekly_return_%"]
                positive = returns[returns > 0]
                negative = returns[returns < 0]
                payload["distribuzione_rendimenti"] = {
                    "settimane_positive": len(positive),
                    "settimane_negative": len(negative),
                    "settimane_zero": len(returns) - len(positive) - len(negative),
                    "media_settimane_positive_%": round(positive.mean(), 2) if len(positive) > 0 else 0,
                    "media_settimane_negative_%": round(negative.mean(), 2) if len(negative) > 0 else 0,
                }

            if "reason" in history.columns:
                reasons = history["reason"].value_counts().to_dict()
                payload["motivi_rotazione"] = {
                    str(k): int(v) for k, v in reasons.items()
                }

    return payload


def generate_prompt(
    portfolio_history: pd.DataFrame,
    portfolio_metrics: dict,
    strategy_config: dict,
    market_label: str = ""
) -> str:
    """Generate a complete LLM prompt with embedded JSON data."""

    payload = build_backtest_payload(
        portfolio_history=portfolio_history,
        portfolio_metrics=portfolio_metrics,
        strategy_config=strategy_config,
        market_label=market_label
    )

    json_block = json.dumps(payload, indent=2, ensure_ascii=False)

    config_keys_list = "\n".join(
        f"  - {k}: {v}" for k, v in strategy_config.items()
    )

    prompt = f"""Sei un consulente esperto di trading quantitativo e ottimizzazione di strategie.

## CONTESTO

Sto usando una strategia momentum/trend-following con rotazione settimanale.
Il sistema seleziona asset in base a medie mobili, RSI, volatilità (ATR) e un punteggio composito (ai_score).
Ogni settimana il motore scansiona l'universo di asset, assegna un punteggio e decide se entrare, mantenere o uscire.

## PARAMETRI ATTUALI DELLA STRATEGIA

Questi sono i parametri configurabili che controllano il comportamento della strategia:

{config_keys_list}

## RISULTATI BACKTEST (JSON)

```json
{json_block}
```

## COSA DEVI FARE

Analizza i risultati del backtest e la configurazione attuale della strategia.
Il tuo obiettivo è **proporre una nuova configurazione ottimizzata** per migliorare la performance.

### STEP 1 — DIAGNOSI
Identifica i problemi principali della strategia guardando:
- Rendimento totale vs tempo investito (efficienza del capitale)
- Max drawdown e rapporto rendimento/rischio
- Win rate settimanale e distribuzione dei rendimenti
- Tempo passato in cash (opportunità perse vs protezione)
- Performance per singolo ticker (quali asset hanno funzionato e quali no)
- Motivi di rotazione (troppi switch? troppo pochi?)

### STEP 2 — CONFIGURAZIONE OTTIMIZZATA
Proponi la nuova configurazione completa come **file JSON pronto per l'importazione**.
Il JSON deve contenere TUTTI i parametri — anche quelli che non hai modificato.
Questo file verrà importato direttamente nel sistema, quindi deve essere un JSON
valido e completo senza commenti, senza "..." e senza valori mancanti.

Genera il blocco JSON esatto qui sotto (copia-incollabile in un file .json):

```json
{{
  "ma_type": "...",
  "fast_ma_period": ...,
  "slow_ma_period": ...,
  "long_ma_period": ...,
  "rsi_period": ...,
  "rsi_buy_min": ...,
  "rsi_buy_max": ...,
  "rsi_sell_above": ...,
  "atr_period": ...,
  "max_volatility_pct": ...,
  "adx_period": ...,
  "adx_min": ...,
  "use_adx_filter": ...,
  "macd_fast": ...,
  "macd_slow": ...,
  "macd_signal": ...,
  "use_macd_filter": ...,
  "volume_sma_period": ...,
  "volume_ratio_min": ...,
  "use_volume_filter": ...,
  "min_ai_score": ...,
  "min_scanner_score": ...,
  "min_hold_weeks": ...,
  "persistence_weeks": ...,
  "switch_score_margin": ...,
  "top_n_candidates": ...,
  "commission_pct": ...,
  "slippage_pct": ...,
  "use_engine_basket": ...,
  "engine_basket_size": ...
}}
```

**IMPORTANTE**: Sostituisci ogni `...` con il valore ottimizzato (o il valore
originale se lo mantieni). Il risultato deve essere un JSON valido che posso
salvare come file `.json` e importare direttamente nella dashboard.

### STEP 3 — SPIEGAZIONE DELLE MODIFICHE
Per ogni parametro che hai cambiato, spiega:
1. Qual era il valore originale
2. Qual è il nuovo valore proposto
3. Perché questo cambio dovrebbe migliorare la performance
4. Quale metrica specifica ti aspetti che migliori

### STEP 4 — AVVERTENZE
- Indica il rischio di overfitting per ciascuna modifica proposta (basso/medio/alto)
- Suggerisci su quali mercati o periodi ritestare la configurazione ottimizzata
- Se alcuni parametri sono già buoni, dillo esplicitamente e non cambiarli

Rispondi in italiano. Sii concreto e specifico — niente consigli generici."""

    return prompt


def _format_strategy_config(config: dict) -> dict:
    """Format strategy config for readability."""
    labels = {
        "ma_type": "tipo_media_mobile",
        "fast_ma_period": "periodo_media_veloce",
        "slow_ma_period": "periodo_media_lenta",
        "long_ma_period": "periodo_media_lunga",
        "rsi_period": "periodo_rsi",
        "rsi_buy_min": "rsi_minimo_acquisto",
        "rsi_buy_max": "rsi_massimo_acquisto",
        "rsi_sell_above": "rsi_vendita_sopra",
        "atr_period": "periodo_atr",
        "max_volatility_pct": "volatilita_massima_%",
        "adx_period": "periodo_adx",
        "adx_min": "adx_minimo",
        "use_adx_filter": "filtro_adx_attivo",
        "use_macd_filter": "filtro_macd_attivo",
        "use_volume_filter": "filtro_volume_attivo",
        "volume_ratio_min": "rapporto_volume_minimo",
        "min_ai_score": "punteggio_ai_minimo",
    }
    result = {}
    for key, value in config.items():
        label = labels.get(key, key)
        result[label] = value
    return result


def _format_metrics(metrics: dict) -> dict:
    """Format metrics with Italian labels."""
    labels = {
        "initial_capital": "capitale_iniziale",
        "final_capital": "capitale_finale",
        "total_return_%": "rendimento_totale_%",
        "max_drawdown_%": "max_drawdown_%",
        "weekly_win_rate_%": "win_rate_settimanale_%",
        "best_week_%": "miglior_settimana_%",
        "worst_week_%": "peggior_settimana_%",
        "rotations": "rotazioni",
        "cash_weeks": "settimane_cash",
        "cash_time_%": "tempo_cash_%",
    }
    result = {}
    for key, value in metrics.items():
        label = labels.get(key, key)
        result[label] = value
    return result


def _compute_ticker_stats(active_history: pd.DataFrame) -> list:
    """Compute per-ticker stats from active history."""
    stats = []
    for ticker, group in active_history.groupby("ticker"):
        entry = {"ticker": ticker, "settimane": len(group)}

        if "weekly_return_%" in group.columns:
            returns = group["weekly_return_%"]
            entry["rendimento_medio_%"] = round(returns.mean(), 2)
            entry["rendimento_totale_%"] = round(returns.sum(), 2)

        if "reason" in group.columns:
            entry["motivi"] = {
                str(k): int(v)
                for k, v in group["reason"].value_counts().to_dict().items()
            }

        stats.append(entry)

    stats.sort(key=lambda x: x.get("rendimento_totale_%", 0), reverse=True)
    return stats
