import pandas as pd

from market_data import download_data
from indicators import add_indicators
from ai_filter import calculate_ai_score
from strategy import generate_signals
from portfolio_scanner import build_scanner_row


def scan_market_on_date(
    tickers: list,
    scan_date,
    strategy_config: dict | None = None
) -> pd.DataFrame:

    results = []
    scan_date = pd.to_datetime(scan_date)

    for ticker in tickers:
        try:
            data = download_data(ticker)
            data = add_indicators(data, strategy_config=strategy_config)
            data = calculate_ai_score(data, strategy_config=strategy_config)
            data = generate_signals(data, strategy_config=strategy_config)

            historical_data = data[data["date"] <= scan_date]

            if historical_data.empty:
                continue

            latest = historical_data.iloc[-1]

            row = build_scanner_row(ticker, latest)
            row["date"] = latest["date"]
            results.append(row)

        except Exception as e:
            print(f"Errore scanner {ticker}: {e}")

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        results_df = results_df.sort_values(
            by="scanner_score",
            ascending=False
        ).reset_index(drop=True)

    return results_df
