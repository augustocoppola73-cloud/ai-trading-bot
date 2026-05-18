import yfinance as yf
import pandas as pd

from market_cache import load_price_data, save_price_data, save_price_data_bulk


BULK_DOWNLOAD_BATCH_SIZE = 100


def normalize_downloaded_data(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    df.columns = [
        str(col).lower().replace(" ", "_")
        for col in df.columns
    ]

    return df


def cache_is_fresh(data: pd.DataFrame) -> bool:
    if data.empty or "date" not in data.columns:
        return False

    latest_date = pd.to_datetime(data["date"]).max().date()
    today = pd.Timestamp.today().date()

    return (today - latest_date).days <= 1


def download_data(
    ticker: str,
    period: str = "5y",
    interval: str = "1d"
) -> pd.DataFrame:
    use_cache = interval == "1d"

    if use_cache:
        cached_data = load_price_data(ticker=ticker, interval=interval)

        if cache_is_fresh(cached_data):
            return cached_data

    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True
    )

    if df.empty:
        raise ValueError(f"Nessun dato trovato per {ticker}")

    df = normalize_downloaded_data(df)

    if use_cache:
        save_price_data(
            ticker=ticker,
            interval=interval,
            data=df
        )

    return df


def extract_downloaded_ticker_data(
    downloaded_data: pd.DataFrame,
    ticker: str,
    single_ticker: bool = False
) -> pd.DataFrame:
    if downloaded_data.empty:
        return pd.DataFrame()

    ticker_data = pd.DataFrame()

    if isinstance(downloaded_data.columns, pd.MultiIndex):
        first_level = [str(item) for item in downloaded_data.columns.get_level_values(0)]
        second_level = [str(item) for item in downloaded_data.columns.get_level_values(1)]

        if ticker in first_level:
            ticker_data = downloaded_data[ticker]
        elif ticker in second_level:
            ticker_data = downloaded_data.xs(ticker, axis=1, level=1)
    elif single_ticker:
        ticker_data = downloaded_data

    if ticker_data.empty:
        return ticker_data

    ticker_data = ticker_data.dropna(how="all")

    if ticker_data.empty:
        return ticker_data

    return normalize_downloaded_data(ticker_data)


def download_data_bulk(
    tickers: list,
    period: str = "5y",
    interval: str = "1d",
    batch_size: int = BULK_DOWNLOAD_BATCH_SIZE,
    progress_callback=None,
    progress_context: dict | None = None
) -> tuple[dict, list]:
    downloaded_by_ticker = {}
    failed_tickers = []
    unique_tickers = list(dict.fromkeys(tickers))

    for start in range(0, len(unique_tickers), batch_size):
        ticker_batch = unique_tickers[start:start + batch_size]
        batch_index = (start // batch_size) + 1
        batch_total = (len(unique_tickers) + batch_size - 1) // batch_size

        try:
            downloaded_data = yf.download(
                tickers=ticker_batch,
                period=period,
                interval=interval,
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False
            )

            batch_results = {}
            single_ticker = len(ticker_batch) == 1

            for ticker in ticker_batch:
                ticker_data = extract_downloaded_ticker_data(
                    downloaded_data=downloaded_data,
                    ticker=ticker,
                    single_ticker=single_ticker
                )

                if ticker_data.empty:
                    failed_tickers.append(ticker)
                    continue

                batch_results[ticker] = ticker_data

            if interval == "1d":
                save_price_data_bulk(
                    data_by_ticker=batch_results,
                    interval=interval
                )

            downloaded_by_ticker.update(batch_results)

        except Exception:
            for ticker in ticker_batch:
                try:
                    ticker_data = download_data(
                        ticker=ticker,
                        period=period,
                        interval=interval
                    )
                    downloaded_by_ticker[ticker] = ticker_data
                except Exception:
                    failed_tickers.append(ticker)

        if progress_callback:
            progress_callback({
                "phase": "Download prezzi",
                "batch_index": batch_index,
                "batch_total": batch_total,
                "ticker_total": len(unique_tickers),
                "loaded_tickers": len(downloaded_by_ticker),
                "skipped_tickers": len(failed_tickers),
                "step_increment": len(ticker_batch),
                **(progress_context or {})
            })

    return downloaded_by_ticker, failed_tickers
