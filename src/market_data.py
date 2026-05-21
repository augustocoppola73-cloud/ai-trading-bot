import yfinance as yf
import pandas as pd

from market_cache import load_price_data, save_price_data, save_price_data_bulk


BULK_DOWNLOAD_BATCH_SIZE = 100
INCREMENTAL_DOWNLOAD_OVERLAP_DAYS = 7


def build_incremental_start_date(
    last_date,
    overlap_days: int = INCREMENTAL_DOWNLOAD_OVERLAP_DAYS
) -> str | None:
    if last_date is None:
        return None

    parsed_date = pd.to_datetime(last_date, errors="coerce")
    if pd.isna(parsed_date):
        return None

    start_date = parsed_date.normalize() - pd.Timedelta(days=overlap_days)

    return start_date.date().isoformat()


def flatten_downloaded_columns(columns) -> list:
    if not isinstance(columns, pd.MultiIndex):
        return list(columns)

    price_fields = {
        "open",
        "high",
        "low",
        "close",
        "adj close",
        "volume"
    }

    for level_index in range(columns.nlevels):
        level_values = [
            str(value).strip().lower()
            for value in columns.get_level_values(level_index)
        ]
        if any(value in price_fields for value in level_values):
            return list(columns.get_level_values(level_index))

    return list(columns.get_level_values(0))


def normalize_downloaded_data(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = flatten_downloaded_columns(df.columns)

    df = df.reset_index()

    df.columns = [
        str(col).lower().replace(" ", "_")
        for col in df.columns
    ]

    date_aliases = ["date", "datetime", "index"]
    date_column = next(
        (column for column in date_aliases if column in df.columns),
        None
    )

    if date_column and date_column != "date":
        df = df.rename(columns={date_column: "date"})

    if "adj_close" in df.columns and "close" not in df.columns:
        df = df.rename(columns={"adj_close": "close"})

    required_columns = ["date", "open", "high", "low", "close", "volume"]
    for column in required_columns:
        if column not in df.columns:
            df[column] = pd.NA

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = (
        df
        .dropna(subset=["date", "open", "high", "low", "close"])
        .sort_values("date")
        .reset_index(drop=True)
    )

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
    interval: str = "1d",
    start: str | None = None,
    end: str | None = None
) -> pd.DataFrame:
    use_cache = interval == "1d"

    if use_cache and start is None and end is None:
        cached_data = load_price_data(ticker=ticker, interval=interval)

        if cache_is_fresh(cached_data):
            return cached_data

    download_kwargs = {
        "tickers": ticker,
        "interval": interval,
        "auto_adjust": True
    }
    if start is not None:
        download_kwargs["start"] = start
    if end is not None:
        download_kwargs["end"] = end
    if start is None and end is None:
        download_kwargs["period"] = period

    df = yf.download(**download_kwargs)

    if df.empty:
        raise ValueError(f"Nessun dato trovato per {ticker}")

    df = normalize_downloaded_data(df)

    if use_cache:
        if start is None and end is None:
            save_price_data(
                ticker=ticker,
                interval=interval,
                data=df
            )
        else:
            save_price_data_bulk({ticker: df}, interval=interval)

    return df


def merge_price_data(
    existing_data: pd.DataFrame | None,
    new_data: pd.DataFrame | None
) -> pd.DataFrame:
    if existing_data is None or existing_data.empty:
        if new_data is None:
            return pd.DataFrame()
        return new_data.copy()

    if new_data is None or new_data.empty:
        return existing_data.copy()

    merged_data = pd.concat(
        [existing_data.copy(), new_data.copy()],
        ignore_index=True
    )
    merged_data["date"] = pd.to_datetime(merged_data["date"])

    return (
        merged_data
        .drop_duplicates(subset=["date"], keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )


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
    start: str | None = None,
    end: str | None = None,
    progress_callback=None,
    progress_context: dict | None = None
) -> tuple[dict, list]:
    downloaded_by_ticker = {}
    failed_tickers = []
    unique_tickers = list(dict.fromkeys(tickers))

    for batch_start in range(0, len(unique_tickers), batch_size):
        ticker_batch = unique_tickers[batch_start:batch_start + batch_size]
        batch_index = (batch_start // batch_size) + 1
        batch_total = (len(unique_tickers) + batch_size - 1) // batch_size

        try:
            download_kwargs = {
                "tickers": ticker_batch,
                "interval": interval,
                "auto_adjust": True,
                "group_by": "ticker",
                "threads": True,
                "progress": False
            }
            if start is not None:
                download_kwargs["start"] = start
            if end is not None:
                download_kwargs["end"] = end
            if start is None and end is None:
                download_kwargs["period"] = period

            downloaded_data = yf.download(**download_kwargs)

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
                        interval=interval,
                        start=start,
                        end=end
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
