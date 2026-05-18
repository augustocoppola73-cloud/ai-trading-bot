import pandas as pd

from market_data import download_data
from indicators import add_indicators
from ai_filter import calculate_ai_score
from strategy import generate_signals


def safe_numeric(value, default=0):
    if pd.isna(value):
        return default

    return value


def compute_scanner_score(latest):

    score = 0

    score += latest["ai_score"]

    if latest["market_regime"] == "BULL":
        score += 20
    elif latest["market_regime"] == "SIDEWAYS":
        score += 5

    if latest["signal"] == "BUY":
        score += 30
    elif latest["signal"] == "HOLD":
        score += 10

    fast_ma = latest.get("trend_fast_ma", latest.get("ema_20"))
    slow_ma = latest.get("trend_slow_ma", latest.get("ema_50"))

    ema_distance = ((fast_ma - slow_ma) / slow_ma) * 100

    score += ema_distance * 5

    if latest["rsi"] > 75:
        score -= 15
    elif latest["rsi"] > 70:
        score -= 5

    volatility_pct = latest["atr"] / latest["close"]

    if volatility_pct > 0.10:
        score -= 60
    elif volatility_pct > 0.07:
        score -= 40
    elif volatility_pct > 0.05:
        score -= 25
    elif volatility_pct > 0.03:
        score -= 10

    if latest.get("adx", 0) >= 25:
        score += 5

    if latest.get("macd_hist", 0) > 0:
        score += 5

    if latest.get("volume_ratio", 0) >= 1:
        score += 5

    bb_percent_b = latest.get("bb_percent_b")

    if pd.notna(bb_percent_b):
        if 0.2 <= bb_percent_b <= 0.85:
            score += 8
        elif bb_percent_b > 1.0:
            score -= 12
        elif bb_percent_b < 0:
            score -= 5

    bb_bandwidth = latest.get("bb_bandwidth")

    if pd.notna(bb_bandwidth) and bb_bandwidth > 30:
        score -= 8

    return round(score, 2)


def build_opportunity_profile(latest, scanner_score: float) -> dict:
    signal = latest["signal"]
    regime = latest["market_regime"]
    volatility_pct = (latest["atr"] / latest["close"]) * 100
    bb_percent_b = latest.get("bb_percent_b")
    volume_ratio = safe_numeric(latest.get("volume_ratio", 0))
    macd_hist = safe_numeric(latest.get("macd_hist", 0))
    adx = safe_numeric(latest.get("adx", 0))

    setup_score = scanner_score
    reasons = []

    if signal == "BUY":
        setup_score += 15
        reasons.append("BUY tecnico")
    elif signal == "SELL":
        setup_score -= 20
        reasons.append("SELL/uscita")
    else:
        reasons.append("HOLD")

    if regime == "BULL":
        setup_score += 10
        reasons.append("regime BULL")
    elif regime == "BEAR":
        setup_score -= 15
        reasons.append("regime BEAR")
    else:
        reasons.append("regime laterale")

    if adx >= 25:
        setup_score += 5
        reasons.append("trend forte")

    if macd_hist > 0:
        setup_score += 5
        reasons.append("MACD positivo")
    else:
        reasons.append("MACD debole")

    if volume_ratio >= 1:
        setup_score += 4
        reasons.append("volume sopra media")

    if pd.notna(bb_percent_b):
        if bb_percent_b > 1:
            setup_score -= 12
            reasons.append("prezzo oltre Bollinger alta")
        elif bb_percent_b >= 0.85:
            setup_score -= 5
            reasons.append("prezzo vicino Bollinger alta")
        elif 0.2 <= bb_percent_b <= 0.85:
            setup_score += 6
            reasons.append("Bollinger equilibrate")
        elif bb_percent_b < 0:
            setup_score -= 5
            reasons.append("prezzo sotto Bollinger bassa")

    if volatility_pct > 10:
        setup_score -= 20
        reasons.append("volatilita molto alta")
    elif volatility_pct > 6:
        setup_score -= 10
        reasons.append("volatilita alta")
    else:
        reasons.append("volatilita accettabile")

    if signal == "SELL":
        opportunity_label = "SELL / Exit Watch"
    elif signal == "BUY" and regime == "BULL" and setup_score >= 150:
        opportunity_label = "Strong BUY"
    elif signal == "BUY" and regime == "BULL" and setup_score >= 120:
        opportunity_label = "BUY"
    elif regime == "BULL" and setup_score >= 100:
        opportunity_label = "Watchlist"
    else:
        opportunity_label = "Weak / Avoid"

    return {
        "setup_score": round(setup_score, 2),
        "opportunity_label": opportunity_label,
        "reason": "; ".join(reasons)
    }


def build_scanner_row(ticker: str, latest) -> dict:
    scanner_score = compute_scanner_score(latest)
    volatility_pct = latest["atr"] / latest["close"]
    opportunity_profile = build_opportunity_profile(
        latest=latest,
        scanner_score=scanner_score
    )

    return {
        "ticker": ticker,
        "data_ultima_chiusura": (
            pd.to_datetime(latest["date"]).date().isoformat()
            if "date" in latest and pd.notna(latest["date"])
            else None
        ),
        "close": round(latest["close"], 2),
        "atr": round(latest["atr"], 4),
        "volatility_%": round(volatility_pct * 100, 2),
        "scanner_score": scanner_score,
        "setup_score": opportunity_profile["setup_score"],
        "opportunity_label": opportunity_profile["opportunity_label"],
        "reason": opportunity_profile["reason"],
        "ai_score": latest["ai_score"],
        "market_regime": latest["market_regime"],
        "signal": latest["signal"],
        "rsi": round(latest["rsi"], 2),
        "adx": round(latest.get("adx", 0), 2),
        "macd": round(latest.get("macd", 0), 4),
        "macd_hist": round(latest.get("macd_hist", 0), 4),
        "volume_ratio": round(latest.get("volume_ratio", 0), 2),
        "bb_lower": round(latest.get("bb_lower", 0), 4),
        "bb_middle": round(latest.get("bb_middle", 0), 4),
        "bb_upper": round(latest.get("bb_upper", 0), 4),
        "bb_bandwidth": round(latest.get("bb_bandwidth", 0), 2),
        "bb_percent_b": round(latest.get("bb_percent_b", 0), 2)
    }


def scan_market(tickers: list, strategy_config: dict | None = None):

    results = []

    for ticker in tickers:

        try:
            data = download_data(ticker)
            data = add_indicators(data, strategy_config=strategy_config)
            data = calculate_ai_score(data, strategy_config=strategy_config)
            data = generate_signals(data, strategy_config=strategy_config)

            latest = data.iloc[-1]
            results.append(build_scanner_row(ticker, latest))

        except Exception as e:
            print(f"Errore su {ticker}: {e}")

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df = results_df.sort_values(
            by=["setup_score", "scanner_score"],
            ascending=[False, False]
        ).reset_index(drop=True)

    return results_df
