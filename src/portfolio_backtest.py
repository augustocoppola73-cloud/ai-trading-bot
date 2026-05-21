import hashlib

import pandas as pd

from market_cache import load_price_data_bulk
from market_data import (
    build_incremental_start_date,
    download_data_bulk,
    merge_price_data
)
from indicators import add_indicators
from ai_filter import calculate_ai_score
from strategy import generate_signals
from portfolio_scanner import build_scanner_row


def build_price_data_session_key(
    tickers: list,
    interval: str = "1d",
    freshness_date=None
) -> str:
    unique_tickers = sorted(set(tickers))
    freshness_value = freshness_date or pd.Timestamp.today().date().isoformat()
    payload = "|".join([interval, str(freshness_value)] + unique_tickers)

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_market_price_data(
    tickers: list,
    progress_callback=None,
    progress_context: dict | None = None,
    interval: str = "1d",
    return_metadata: bool = False,
    download_missing: bool = True
) -> dict | tuple[dict, dict]:
    unique_tickers = list(dict.fromkeys(tickers))
    price_data_by_ticker, cache_status = load_price_data_bulk(
        tickers=unique_tickers,
        interval=interval
    )

    fresh_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "loaded"
    ]
    stale_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "stale"
    ]
    missing_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "missing"
    ]
    invalid_tickers = [
        ticker for ticker, item in cache_status.items()
        if item["status"] == "invalid"
    ]

    if progress_callback:
        progress_callback({
            "phase": "Lettura cache prezzi",
            "ticker_total": len(unique_tickers),
            "loaded_tickers": len(fresh_tickers),
            "stale_tickers": len(stale_tickers),
            "missing_tickers": len(missing_tickers),
            "skipped_tickers": len(invalid_tickers),
            "step_increment": len(fresh_tickers),
            **(progress_context or {})
        })

    tickers_to_download = stale_tickers + missing_tickers + invalid_tickers
    downloaded_by_ticker = {}
    failed_downloads = []

    if tickers_to_download and download_missing:
        full_download_tickers = missing_tickers + invalid_tickers

        if full_download_tickers:
            full_downloads, full_failures = download_data_bulk(
                tickers=full_download_tickers,
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
                interval=interval,
                start=incremental_start,
                progress_callback=progress_callback,
                progress_context=progress_context
            )
            downloaded_by_ticker.update(incremental_downloads)
            failed_downloads.extend(incremental_failures)

        for ticker, data in downloaded_by_ticker.items():
            data = data.copy()
            data["date"] = pd.to_datetime(data["date"])
            data = data.sort_values("date").reset_index(drop=True)
            price_data_by_ticker[ticker] = merge_price_data(
                price_data_by_ticker.get(ticker),
                data
            )

    for ticker in invalid_tickers:
        if ticker not in downloaded_by_ticker:
            price_data_by_ticker.pop(ticker, None)

    for ticker, data in list(price_data_by_ticker.items()):
        data = data.copy()
        data["date"] = pd.to_datetime(data["date"])
        price_data_by_ticker[ticker] = (
            data.sort_values("date").reset_index(drop=True)
        )

    excluded_tickers = [
        ticker for ticker in unique_tickers
        if ticker not in price_data_by_ticker
    ]
    metadata = {
        "requested": len(unique_tickers),
        "from_cache": len(fresh_tickers),
        "stale_from_cache": len(stale_tickers),
        "missing_from_cache": len(missing_tickers),
        "invalid_from_cache": len(invalid_tickers),
        "download_missing": download_missing,
        "downloaded": len(downloaded_by_ticker),
        "failed_downloads": len(set(failed_downloads)),
        "loaded": len(price_data_by_ticker),
        "excluded": len(excluded_tickers),
        "excluded_tickers": excluded_tickers
    }

    if return_metadata:
        return price_data_by_ticker, metadata

    return price_data_by_ticker


def prepare_market_data(
    tickers: list,
    strategy_config: dict | None = None,
    progress_callback=None,
    progress_context: dict | None = None
) -> dict:
    price_data_by_ticker = load_market_price_data(
        tickers=tickers,
        progress_callback=progress_callback,
        progress_context=progress_context
    )
    market_data, _, _ = prepare_strategy_market_data(
        price_data_by_ticker=price_data_by_ticker,
        strategy_config=strategy_config
    )

    return market_data


def prepare_strategy_market_data(
    price_data_by_ticker: dict,
    strategy_config: dict | None = None,
    rebalance_dates=None,
    progress_callback=None,
    progress_context: dict | None = None
) -> tuple[dict, dict, list]:
    market_data = {}
    failed_tickers = []

    ticker_items = list(price_data_by_ticker.items())

    for index, (ticker, price_data) in enumerate(ticker_items, start=1):
        try:
            data = price_data.copy()
            data = add_indicators(data, strategy_config=strategy_config)
            data = calculate_ai_score(data, strategy_config=strategy_config)
            data = generate_signals(data, strategy_config=strategy_config)

            market_data[ticker] = data
            print(f"Prepared {ticker}")

        except Exception as e:
            failed_tickers.append(ticker)
            print(f"Errore preparazione {ticker}: {e}")

        if progress_callback:
            progress_callback({
                "phase": "Preparazione strategia",
                "ticker": ticker,
                "ticker_index": index,
                "ticker_total": len(ticker_items),
                "prepared_tickers": len(market_data),
                "skipped_tickers": len(failed_tickers),
                "step_increment": 1,
                **(progress_context or {})
            })

    scanner_by_date = {}

    if rebalance_dates is not None:
        scanner_by_date = build_rebalance_scanners(
            market_data=market_data,
            rebalance_dates=rebalance_dates
        )

    return market_data, scanner_by_date, failed_tickers


def build_rebalance_scanners(
    market_data: dict,
    rebalance_dates
) -> dict:
    rebalance_dates = pd.DatetimeIndex(pd.to_datetime(rebalance_dates))
    results_by_date = {
        scan_date: []
        for scan_date in rebalance_dates
    }

    for ticker, data in market_data.items():
        if data.empty:
            continue

        data = data.sort_values("date").reset_index(drop=True)
        available_dates = pd.DatetimeIndex(pd.to_datetime(data["date"]))
        latest_positions = available_dates.searchsorted(
            rebalance_dates,
            side="right"
        ) - 1

        for scan_date, latest_position in zip(rebalance_dates, latest_positions):
            if latest_position < 0:
                continue

            latest = data.iloc[latest_position]
            row = build_scanner_row(ticker, latest)
            row["date"] = latest["date"]
            results_by_date[scan_date].append(row)

    scanner_by_date = {}

    for scan_date, rows in results_by_date.items():
        results_df = pd.DataFrame(rows)

        if not results_df.empty:
            results_df = results_df.sort_values(
                by="scanner_score",
                ascending=False
            ).reset_index(drop=True)

        scanner_by_date[scan_date] = results_df

    return scanner_by_date


def scan_preloaded_market_on_date(
    market_data: dict,
    scan_date
) -> pd.DataFrame:

    results = []
    scan_date = pd.to_datetime(scan_date)

    for ticker, data in market_data.items():

        historical_data = data[data["date"] <= scan_date]

        if historical_data.empty:
            continue

        latest = historical_data.iloc[-1]

        row = build_scanner_row(ticker, latest)
        row["date"] = latest["date"]
        results.append(row)

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df = results_df.sort_values(
            by="scanner_score",
            ascending=False
        ).reset_index(drop=True)

    return results_df


def get_valid_candidates(
    scanner: pd.DataFrame,
    min_scanner_score: float,
    max_volatility_pct: float,
    top_n_candidates: int
) -> pd.DataFrame:

    if scanner.empty:
        return pd.DataFrame()

    candidates = scanner[
        (scanner["signal"] == "BUY") &
        (scanner["market_regime"] == "BULL") &
        (scanner["scanner_score"] >= min_scanner_score) &
        (scanner["volatility_%"] <= max_volatility_pct)
    ].copy()

    candidates = candidates.sort_values(
        by="scanner_score",
        ascending=False
    ).head(top_n_candidates)

    return candidates


def run_portfolio_backtest(
    tickers: list,
    start_date: str,
    end_date: str,
    initial_capital: float = 1000,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.001,
    min_hold_weeks: int = 4,
    max_volatility_pct: float = 6.0,
    min_scanner_score: float = 100,
    persistence_weeks: int = 2,
    switch_score_margin: float = 15.0,
    top_n_candidates: int = 5,
    strategy_config: dict | None = None,
    progress_callback=None,
    progress_context: dict | None = None,
    price_data_by_ticker: dict | None = None,
    return_details: bool = False
):

    capital = initial_capital
    portfolio_history = []

    current_ticker = None
    weeks_held = 0

    candidate_streaks = {}

    rebalance_dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="W-MON"
    )

    if price_data_by_ticker is None:
        price_data_by_ticker = load_market_price_data(
            tickers=tickers,
            progress_callback=progress_callback,
            progress_context=progress_context
        )

    market_data, scanner_by_date, failed_tickers = prepare_strategy_market_data(
        price_data_by_ticker=price_data_by_ticker,
        strategy_config=strategy_config,
        rebalance_dates=rebalance_dates,
        progress_callback=progress_callback,
        progress_context=progress_context
    )

    if failed_tickers and progress_callback:
        progress_callback({
            "phase": "Preparazione strategia",
            "skipped_tickers": len(failed_tickers),
            "step_increment": 0,
            **(progress_context or {})
        })

    total_weeks = max(len(rebalance_dates) - 1, 0)

    for i in range(total_weeks):

        scan_date = rebalance_dates[i]
        next_date = rebalance_dates[i + 1]

        if progress_callback:
            progress_callback({
                "phase": "Simulazione settimane",
                "week_index": i + 1,
                "week_total": total_weeks,
                "scan_date": scan_date.date(),
                "step_increment": 1,
                **(progress_context or {})
            })

        scanner = scanner_by_date.get(scan_date, pd.DataFrame())

        chosen_ticker = current_ticker
        reason = "HOLD_EXISTING"
        force_exit = False

        candidates = get_valid_candidates(
            scanner=scanner,
            min_scanner_score=min_scanner_score,
            max_volatility_pct=max_volatility_pct,
            top_n_candidates=top_n_candidates
        )

        valid_tickers = set(candidates["ticker"].tolist())

        for ticker in list(candidate_streaks.keys()):
            if ticker not in valid_tickers:
                candidate_streaks[ticker] = 0

        for ticker in valid_tickers:
            candidate_streaks[ticker] = candidate_streaks.get(ticker, 0) + 1

        can_switch = (
            current_ticker is None
            or weeks_held >= min_hold_weeks
        )

        current_score = None

        if current_ticker is not None and not scanner.empty:

            current_asset_scan = scanner[
                scanner["ticker"] == current_ticker
            ]

            if not current_asset_scan.empty:

                current_asset_scan = current_asset_scan.iloc[0]

                current_score = current_asset_scan["scanner_score"]

                weak_regime = current_asset_scan["market_regime"] == "BEAR"
                weak_signal = current_asset_scan["signal"] == "SELL"
                weak_score = current_asset_scan["scanner_score"] < min_scanner_score
                excessive_volatility = current_asset_scan["volatility_%"] > max_volatility_pct

                if weak_regime or weak_signal or weak_score or excessive_volatility:
                    force_exit = True
                    can_switch = True
                    reason = "FORCED_ROTATION"

        if can_switch:

            if not candidates.empty:

                persistent_candidates = candidates[
                    candidates["ticker"].apply(
                        lambda t: candidate_streaks.get(t, 0) >= persistence_weeks
                    )
                ]

                if not persistent_candidates.empty:

                    best_candidate = persistent_candidates.iloc[0]
                    best_ticker = best_candidate["ticker"]
                    best_score = best_candidate["scanner_score"]

                    should_switch = False

                    if current_ticker is None:
                        should_switch = True
                    elif force_exit:
                        should_switch = True
                    elif best_ticker == current_ticker:
                        should_switch = False
                    elif current_score is None:
                        should_switch = True
                    elif best_score >= current_score + switch_score_margin:
                        should_switch = True

                    if should_switch:
                        chosen_ticker = best_ticker

                        if force_exit:
                            reason = "FORCED_ROTATION"
                        elif current_ticker is None:
                            reason = "NEW_SELECTION"
                        else:
                            reason = "ROTATION_STRONGER_ASSET"

                        weeks_held = 0

                    else:
                        chosen_ticker = current_ticker
                        reason = "HOLD_EXISTING_BETTER_THAN_SWITCH"

                elif current_ticker is None or force_exit:
                    chosen_ticker = "CASH"

                    if force_exit:
                        reason = "FORCED_TO_CASH"
                    else:
                        reason = "NO_PERSISTENT_BUY_SIGNAL"

            else:
                if current_ticker is None or force_exit:
                    chosen_ticker = "CASH"

                    if force_exit:
                        reason = "FORCED_TO_CASH"
                    else:
                        reason = "NO_VALID_BUY_SIGNAL"

        if chosen_ticker is None:
            chosen_ticker = "CASH"

        if chosen_ticker == "CASH":

            portfolio_history.append({
                "scan_date": scan_date.date(),
                "ticker": "CASH",
                "reason": reason,
                "weeks_held": 0,
                "entry_price": None,
                "exit_price": None,
                "weekly_return_%": 0,
                "capital": round(capital, 2),
                "gross_return_%": None,
                "net_return_%": None,
                "scanner_score": None,
                "volatility_%": None
            })

            current_ticker = None
            weeks_held = 0
            continue

        asset_data = market_data[chosen_ticker]

        period_data = asset_data[
            (asset_data["date"] >= scan_date) &
            (asset_data["date"] <= next_date)
        ]

        if len(period_data) < 2:
            continue

        asset_scan_row = scanner[
            scanner["ticker"] == chosen_ticker
        ]

        if not asset_scan_row.empty:
            asset_scan_row = asset_scan_row.iloc[0]
            chosen_score = asset_scan_row["scanner_score"]
            chosen_volatility = asset_scan_row["volatility_%"]
        else:
            chosen_score = None
            chosen_volatility = None

        raw_entry_price = period_data.iloc[0]["close"]
        raw_exit_price = period_data.iloc[-1]["close"]

        entry_price = raw_entry_price * (1 + slippage_pct)
        exit_price = raw_exit_price * (1 - slippage_pct)

        gross_return = (exit_price - entry_price) / entry_price

        net_return = gross_return - (commission_pct * 2)

        capital *= (1 + net_return)

        portfolio_history.append({
            "scan_date": scan_date.date(),
            "ticker": chosen_ticker,
            "reason": reason,
            "weeks_held": weeks_held + 1,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "weekly_return_%": round(net_return * 100, 2),
            "capital": round(capital, 2),
            "gross_return_%": round(gross_return * 100, 2),
            "net_return_%": round(net_return * 100, 2),
            "scanner_score": chosen_score,
            "volatility_%": chosen_volatility
        })

        current_ticker = chosen_ticker
        weeks_held += 1

    history_df = pd.DataFrame(portfolio_history)

    if return_details:
        return history_df, round(capital, 2), {
            "market_data": market_data,
            "scanner_by_date": scanner_by_date,
            "failed_tickers": failed_tickers
        }

    return history_df, round(capital, 2)
