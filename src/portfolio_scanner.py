import pandas as pd

from market_cache import load_price_data_bulk
from market_data import download_data
from market_data import (
    build_incremental_start_date,
    download_data_bulk,
    merge_price_data
)
from indicators import add_indicators
from ai_filter import calculate_ai_score
from strategy import generate_signals


MIN_SCANNER_PRICE_ROWS = 220


def safe_numeric(value, default=0):
    if pd.isna(value):
        return default

    return value


def safe_ratio(numerator, denominator, default=0):
    numerator = safe_numeric(numerator, default=None)
    denominator = safe_numeric(denominator, default=None)

    if numerator is None or denominator in [None, 0]:
        return default

    return numerator / denominator


def build_data_quality_profile(
    ticker: str,
    data: pd.DataFrame,
    status: str = "OK",
    reason: str | None = None
) -> dict:
    if data is None or data.empty:
        return {
            "ticker": ticker,
            "data_status": status if status != "OK" else "NO_DATA",
            "data_quality_reason": reason or "No price data available",
            "price_rows": 0,
            "latest_price_date": None,
            "min_history_ok": False
        }

    latest_date = (
        pd.to_datetime(data["date"]).max().date().isoformat()
        if "date" in data.columns and data["date"].notna().any()
        else None
    )
    rows_count = len(data)
    min_history_ok = rows_count >= MIN_SCANNER_PRICE_ROWS

    return {
        "ticker": ticker,
        "data_status": status,
        "data_quality_reason": (
            reason or (
                "OK" if min_history_ok else
                f"History shorter than {MIN_SCANNER_PRICE_ROWS} rows"
            )
        ),
        "price_rows": rows_count,
        "latest_price_date": latest_date,
        "min_history_ok": min_history_ok
    }


def build_invalid_scanner_row(
    ticker: str,
    status: str,
    reason: str,
    data: pd.DataFrame | None = None
) -> dict:
    quality = build_data_quality_profile(
        ticker=ticker,
        data=data if data is not None else pd.DataFrame(),
        status=status,
        reason=reason
    )

    row = {
        **quality,
        "data_ultima_chiusura": quality["latest_price_date"],
        "close": None,
        "atr": None,
        "volatility_%": None,
        "scanner_score": None,
        "setup_score": None,
        "opportunity_label": "No Data",
        "reason": reason,
        "ai_score": None,
        "market_regime": None,
        "signal": None,
        "rsi": None,
        "adx": None,
        "macd": None,
        "macd_hist": None,
        "volume_ratio": None,
        "bb_lower": None,
        "bb_middle": None,
        "bb_upper": None,
        "bb_bandwidth": None,
        "bb_percent_b": None
    }
    row["selection_score"] = None
    row["label_score"] = None
    row["score_schema_version"] = "v1_legacy_additive"
    row.update(build_buy_gate_context(row))
    row["score_consistency_status"] = classify_score_consistency(row)

    return row


def compute_scanner_score(latest):

    score = 0

    score += safe_numeric(latest.get("ai_score", 0))

    if latest.get("market_regime") == "BULL":
        score += 20
    elif latest.get("market_regime") == "SIDEWAYS":
        score += 5

    if latest.get("signal") == "BUY":
        score += 30
    elif latest.get("signal") == "HOLD":
        score += 10

    fast_ma = latest.get("trend_fast_ma", latest.get("ema_20"))
    slow_ma = latest.get("trend_slow_ma", latest.get("ema_50"))

    ema_distance = safe_ratio(fast_ma - slow_ma, slow_ma) * 100

    score += ema_distance * 5

    rsi = safe_numeric(latest.get("rsi", 0))

    if rsi > 75:
        score -= 15
    elif rsi > 70:
        score -= 5

    volatility_pct = safe_ratio(latest.get("atr"), latest.get("close"))

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
    signal = latest.get("signal")
    regime = latest.get("market_regime")
    volatility_pct = safe_ratio(latest.get("atr"), latest.get("close")) * 100
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


def build_buy_gate_context(
    row,
    min_score: float | None = None,
    max_volatility_pct: float | None = None
) -> dict:
    fail_reasons = []

    if row.get("signal") != "BUY":
        fail_reasons.append("SIGNAL_NOT_BUY")

    if row.get("market_regime") != "BULL":
        fail_reasons.append("REGIME_NOT_BULL")

    scanner_score = row.get("scanner_score")
    if min_score is not None and (
        pd.isna(scanner_score) or scanner_score < min_score
    ):
        fail_reasons.append("SCORE_BELOW_MIN")

    volatility_pct = row.get("volatility_%")
    if max_volatility_pct is not None and (
        pd.isna(volatility_pct) or volatility_pct > max_volatility_pct
    ):
        fail_reasons.append("VOLATILITY_TOO_HIGH")

    close = row.get("close")
    if pd.isna(close) or close <= 0:
        fail_reasons.append("INVALID_CLOSE")

    atr = row.get("atr")
    if pd.isna(atr) or atr <= 0:
        fail_reasons.append("INVALID_ATR")

    return {
        "buy_gate_passed": not fail_reasons,
        "buy_gate_fail_reasons": "; ".join(fail_reasons) or "OK"
    }


def classify_score_consistency(row: dict) -> str:
    if row.get("data_status") not in [None, "OK"]:
        return "DATA_NOT_READY"

    if row.get("signal") == "SELL":
        return "SELL_EXIT"

    if row.get("buy_gate_passed"):
        return "CONSISTENT_BUY_GATE"

    if row.get("market_regime") == "BULL" and row.get("setup_score", 0) >= 100:
        return "WATCHLIST_ONLY"

    return "BUY_GATE_FAILED"


def build_scanner_row(
    ticker: str,
    latest,
    quality_profile: dict | None = None
) -> dict:
    scanner_score = compute_scanner_score(latest)
    volatility_pct = safe_ratio(latest.get("atr"), latest.get("close"))
    opportunity_profile = build_opportunity_profile(
        latest=latest,
        scanner_score=scanner_score
    )
    quality = quality_profile or {
        "data_status": "OK",
        "data_quality_reason": "OK",
        "price_rows": None,
        "latest_price_date": (
            pd.to_datetime(latest["date"]).date().isoformat()
            if "date" in latest and pd.notna(latest["date"])
            else None
        ),
        "min_history_ok": None
    }

    row = {
        **quality,
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
    row["selection_score"] = row["scanner_score"]
    row["label_score"] = row["setup_score"]
    row["score_schema_version"] = "v1_legacy_additive"
    row.update(build_buy_gate_context(row))
    row["score_consistency_status"] = classify_score_consistency(row)

    return row


def prepare_scanner_data(
    ticker: str,
    price_data: pd.DataFrame,
    strategy_config: dict | None = None
) -> dict:
    quality = build_data_quality_profile(
        ticker=ticker,
        data=price_data
    )

    if price_data.empty:
        return build_invalid_scanner_row(
            ticker=ticker,
            status="NO_DATA",
            reason="No price data available"
        )

    if not quality["min_history_ok"]:
        return build_invalid_scanner_row(
            ticker=ticker,
            status="INSUFFICIENT_HISTORY",
            reason=quality["data_quality_reason"],
            data=price_data
        )

    data = add_indicators(price_data, strategy_config=strategy_config)
    data = calculate_ai_score(data, strategy_config=strategy_config)
    data = generate_signals(data, strategy_config=strategy_config)
    latest = data.iloc[-1]

    critical_columns = [
        "close",
        "atr",
        "rsi",
        "ai_score",
        "market_regime",
        "signal"
    ]
    missing_critical = [
        column for column in critical_columns
        if column not in latest or pd.isna(latest[column])
    ]

    if missing_critical:
        return build_invalid_scanner_row(
            ticker=ticker,
            status="INVALID_INDICATORS",
            reason="Missing indicators: " + ", ".join(missing_critical),
            data=price_data
        )

    row = build_scanner_row(
        ticker=ticker,
        latest=latest,
        quality_profile=quality
    )

    return row


def sort_scanner_results(results_df: pd.DataFrame) -> pd.DataFrame:
    if results_df.empty:
        return results_df

    for column in ["setup_score", "scanner_score"]:
        if column not in results_df.columns:
            results_df[column] = None

    return results_df.sort_values(
        by=["setup_score", "scanner_score", "ticker"],
        ascending=[False, False, True],
        na_position="last"
    ).reset_index(drop=True)


def load_scanner_price_data_bulk(
    tickers: list,
    period: str = "5y",
    interval: str = "1d",
    download_missing: bool = True,
    progress_callback=None,
    progress_context: dict | None = None
) -> tuple[dict, list]:
    unique_tickers = list(dict.fromkeys(tickers))
    price_data_by_ticker, cache_status = load_price_data_bulk(
        tickers=unique_tickers,
        interval=interval
    )
    missing_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "missing"
    ]
    stale_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "stale"
    ]
    invalid_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "invalid"
    ]
    tickers_to_download = missing_tickers + stale_tickers + invalid_tickers
    failed_downloads = []

    if progress_callback:
        progress_callback({
            "phase": "Lettura cache scanner",
            "ticker_total": len(unique_tickers),
            "loaded_tickers": len(price_data_by_ticker),
            "missing_tickers": len(missing_tickers),
            "stale_tickers": len(stale_tickers),
            "skipped_tickers": len(invalid_tickers),
            "step_increment": 0,
            **(progress_context or {})
        })

    if tickers_to_download and download_missing:
        downloaded_by_ticker = {}
        full_download_tickers = missing_tickers + invalid_tickers

        if full_download_tickers:
            full_downloads, full_failures = download_data_bulk(
                tickers=full_download_tickers,
                period=period,
                interval=interval,
                progress_callback=progress_callback,
                progress_context=progress_context
            )
            downloaded_by_ticker.update(full_downloads)
            failed_downloads.extend(full_failures)

        stale_groups = {}
        for ticker in stale_tickers:
            incremental_start = build_incremental_start_date(
                cache_status.get(ticker, {}).get("last_date")
            )
            stale_groups.setdefault(incremental_start, []).append(ticker)

        for incremental_start, grouped_tickers in stale_groups.items():
            incremental_downloads, incremental_failures = download_data_bulk(
                tickers=grouped_tickers,
                period=period,
                interval=interval,
                start=incremental_start,
                progress_callback=progress_callback,
                progress_context=progress_context
            )
            downloaded_by_ticker.update(incremental_downloads)
            failed_downloads.extend(incremental_failures)

        for ticker, data in downloaded_by_ticker.items():
            price_data_by_ticker[ticker] = merge_price_data(
                price_data_by_ticker.get(ticker),
                data
            )

    for ticker, data in list(price_data_by_ticker.items()):
        data = data.copy()
        if "date" not in data.columns:
            price_data_by_ticker.pop(ticker, None)
            continue
        data["date"] = pd.to_datetime(data["date"])
        price_data_by_ticker[ticker] = data.sort_values("date").reset_index(
            drop=True
        )

    missing_after_load = [
        ticker for ticker in unique_tickers
        if ticker not in price_data_by_ticker
    ]

    return price_data_by_ticker, list(dict.fromkeys(
        failed_downloads + missing_after_load
    ))


def scan_market_from_price_data(
    price_data_by_ticker: dict,
    tickers: list | None = None,
    strategy_config: dict | None = None,
    progress_callback=None,
    progress_context: dict | None = None
) -> pd.DataFrame:
    results = []
    requested_tickers = tickers or list(price_data_by_ticker.keys())
    ticker_total = len(requested_tickers)
    last_progress_index = 0

    for index, ticker in enumerate(requested_tickers, start=1):
        try:
            price_data = price_data_by_ticker.get(ticker, pd.DataFrame())
            results.append(prepare_scanner_data(
                ticker=ticker,
                price_data=price_data,
                strategy_config=strategy_config
            ))
        except Exception as error:
            results.append(build_invalid_scanner_row(
                ticker=ticker,
                status="SCAN_ERROR",
                reason=str(error),
                data=price_data_by_ticker.get(ticker, pd.DataFrame())
            ))

        if progress_callback and (
            index == 1 or index == ticker_total or index % 25 == 0
        ):
            progress_callback({
                "phase": "Analisi scanner",
                "ticker": ticker,
                "ticker_index": index,
                "ticker_total": ticker_total,
                "step_increment": (
                    index - last_progress_index
                ),
                **(progress_context or {})
            })
            last_progress_index = index

    return sort_scanner_results(pd.DataFrame(results))


def scan_market(
    tickers: list,
    strategy_config: dict | None = None,
    use_bulk: bool = True,
    download_missing: bool = True,
    progress_callback=None,
    progress_context: dict | None = None
):

    if use_bulk:
        price_data_by_ticker, failed_tickers = load_scanner_price_data_bulk(
            tickers=tickers,
            download_missing=download_missing,
            progress_callback=progress_callback,
            progress_context=progress_context
        )
        results_df = scan_market_from_price_data(
            price_data_by_ticker=price_data_by_ticker,
            tickers=tickers,
            strategy_config=strategy_config,
            progress_callback=progress_callback,
            progress_context=progress_context
        )

        if failed_tickers and not results_df.empty:
            missing_rows = [
                build_invalid_scanner_row(
                    ticker=ticker,
                    status="DOWNLOAD_FAILED",
                    reason="Price download failed"
                )
                for ticker in failed_tickers
                if ticker not in set(results_df["ticker"].tolist())
            ]
            if missing_rows:
                results_df = pd.concat(
                    [results_df, pd.DataFrame(missing_rows)],
                    ignore_index=True
                )
                results_df = sort_scanner_results(results_df)

        return results_df

    results = []

    for ticker in tickers:

        try:
            data = download_data(ticker)
            results.append(prepare_scanner_data(
                ticker=ticker,
                price_data=data,
                strategy_config=strategy_config
            ))

        except Exception as e:
            results.append(build_invalid_scanner_row(
                ticker=ticker,
                status="SCAN_ERROR",
                reason=str(e)
            ))

    results_df = pd.DataFrame(results)

    return sort_scanner_results(results_df)
