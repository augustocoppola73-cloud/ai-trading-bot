import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


CACHE_PATH = Path("reports/market_data_cache.sqlite")
PRICE_CACHE_CHUNK_SIZE = 500


def get_connection():
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(CACHE_PATH)
    ensure_schema(connection)

    return connection


def ensure_schema(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS universe_cache (
            market TEXT NOT NULL,
            ticker TEXT NOT NULL,
            payload TEXT NOT NULL,
            cached_at TEXT NOT NULL,
            PRIMARY KEY (market, ticker)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS price_cache (
            ticker TEXT NOT NULL,
            interval TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            cached_at TEXT NOT NULL,
            PRIMARY KEY (ticker, interval, date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS symbol_metadata (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            asset_type TEXT,
            exchange_name TEXT,
            currency TEXT,
            source TEXT,
            verified_at TEXT,
            last_error TEXT,
            error_at TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_errors (
            provider TEXT NOT NULL,
            cache_key TEXT NOT NULL,
            error TEXT NOT NULL,
            cached_at TEXT NOT NULL,
            PRIMARY KEY (provider, cache_key)
        )
        """
    )
    connection.commit()


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load_universe_records(market: str) -> list:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT payload
            FROM universe_cache
            WHERE market = ?
            ORDER BY ticker
            """,
            (market,)
        ).fetchall()

    return [json.loads(row[0]) for row in rows]


def save_universe_records(market: str, records: list):
    cached_at = now_iso()

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM universe_cache WHERE market = ?",
            (market,)
        )
        connection.executemany(
            """
            INSERT OR REPLACE INTO universe_cache (
                market, ticker, payload, cached_at
            )
            VALUES (?, ?, ?, ?)
            """,
            [
                (
                    market,
                    record["ticker"],
                    json.dumps(record),
                    cached_at
                )
                for record in records
            ]
        )
        connection.commit()


def load_price_data(ticker: str, interval: str) -> pd.DataFrame:
    with get_connection() as connection:
        data = pd.read_sql_query(
            """
            SELECT date, open, high, low, close, volume
            FROM price_cache
            WHERE ticker = ? AND interval = ?
            ORDER BY date
            """,
            connection,
            params=(ticker, interval)
        )

    if data.empty:
        return data

    data["date"] = pd.to_datetime(data["date"])

    return data


def price_cache_is_fresh(data: pd.DataFrame, fresh_days: int = 1) -> bool:
    if data.empty or "date" not in data.columns:
        return False

    latest_date = pd.to_datetime(data["date"]).max().date()
    today = pd.Timestamp.today().date()

    return (today - latest_date).days <= fresh_days


def load_price_data_bulk(
    tickers: list,
    interval: str = "1d",
    fresh_days: int = 1,
    chunk_size: int = PRICE_CACHE_CHUNK_SIZE
) -> tuple[dict, dict]:
    unique_tickers = list(dict.fromkeys(tickers))
    data_by_ticker = {}
    status = {
        ticker: {
            "status": "missing",
            "last_date": None,
            "rows": 0
        }
        for ticker in unique_tickers
    }

    if not unique_tickers:
        return data_by_ticker, status

    with get_connection() as connection:
        for start in range(0, len(unique_tickers), chunk_size):
            ticker_chunk = unique_tickers[start:start + chunk_size]
            placeholders = ",".join(["?"] * len(ticker_chunk))
            query = f"""
                SELECT ticker, date, open, high, low, close, volume
                FROM price_cache
                WHERE interval = ? AND ticker IN ({placeholders})
                ORDER BY ticker, date
            """
            chunk_data = pd.read_sql_query(
                query,
                connection,
                params=[interval] + ticker_chunk
            )

            if chunk_data.empty:
                continue

            chunk_data["date"] = pd.to_datetime(chunk_data["date"])

            for ticker, ticker_data in chunk_data.groupby("ticker", sort=False):
                price_data = (
                    ticker_data
                    .drop(columns=["ticker"])
                    .sort_values("date")
                    .reset_index(drop=True)
                )
                data_by_ticker[ticker] = price_data

                last_date = price_data["date"].max()
                rows_count = len(price_data)
                has_valid_prices = (
                    "close" in price_data.columns and
                    price_data["close"].notna().any()
                )

                if not has_valid_prices:
                    cache_status = "invalid"
                elif price_cache_is_fresh(price_data, fresh_days=fresh_days):
                    cache_status = "loaded"
                else:
                    cache_status = "stale"

                status[ticker] = {
                    "status": cache_status,
                    "last_date": last_date.strftime("%Y-%m-%d"),
                    "rows": rows_count
                }

    return data_by_ticker, status


def save_price_data(ticker: str, interval: str, data: pd.DataFrame):
    if data.empty:
        return

    cached_at = now_iso()
    price_data = data.copy()
    price_data["ticker"] = ticker
    price_data["interval"] = interval
    price_data["cached_at"] = cached_at
    price_data["date"] = pd.to_datetime(price_data["date"]).dt.strftime(
        "%Y-%m-%d"
    )

    columns = [
        "ticker",
        "interval",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "cached_at"
    ]
    price_data = price_data[columns]

    with get_connection() as connection:
        connection.execute(
            "DELETE FROM price_cache WHERE ticker = ? AND interval = ?",
            (ticker, interval)
        )
        price_data.to_sql(
            "price_cache",
            connection,
            if_exists="append",
            index=False
        )
        connection.commit()


def save_price_data_bulk(data_by_ticker: dict, interval: str):
    if not data_by_ticker:
        return

    cached_at = now_iso()
    frames = []

    for ticker, data in data_by_ticker.items():
        if data is None or data.empty:
            continue

        price_data = data.copy()
        price_data["ticker"] = ticker
        price_data["interval"] = interval
        price_data["cached_at"] = cached_at
        price_data["date"] = pd.to_datetime(price_data["date"]).dt.strftime(
            "%Y-%m-%d"
        )

        columns = [
            "ticker",
            "interval",
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "cached_at"
        ]
        frames.append(price_data[columns])

    if not frames:
        return

    all_price_data = pd.concat(frames, ignore_index=True)
    tickers = list(data_by_ticker.keys())

    with get_connection() as connection:
        connection.executemany(
            "DELETE FROM price_cache WHERE ticker = ? AND interval = ?",
            [(ticker, interval) for ticker in tickers]
        )
        all_price_data.to_sql(
            "price_cache",
            connection,
            if_exists="append",
            index=False
        )
        connection.commit()


def get_price_cache_status(tickers: list, interval: str = "1d") -> dict:
    if not tickers:
        return {}

    status = {}

    with get_connection() as connection:
        for start in range(0, len(tickers), 500):
            ticker_chunk = tickers[start:start + 500]
            placeholders = ",".join(["?"] * len(ticker_chunk))
            rows = connection.execute(
                f"""
                SELECT ticker, MAX(date) AS last_date, COUNT(*) AS rows_count
                FROM price_cache
                WHERE interval = ? AND ticker IN ({placeholders})
                GROUP BY ticker
                """,
                [interval] + ticker_chunk
            ).fetchall()

            for row in rows:
                status[row[0]] = {
                    "last_date": row[1],
                    "rows": row[2]
                }

    return status


def save_symbol_metadata(record: dict):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO symbol_metadata (
                ticker, name, market, asset_type, exchange_name, currency,
                source, verified_at, last_error, error_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.get("ticker"),
                record.get("name"),
                record.get("market"),
                record.get("asset_type"),
                record.get("exchange"),
                record.get("currency"),
                record.get("source"),
                now_iso(),
                None,
                None
            )
        )
        connection.commit()


def load_symbol_metadata() -> list:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT ticker, name, market, asset_type, exchange_name, currency,
                   source
            FROM symbol_metadata
            WHERE last_error IS NULL
            ORDER BY ticker
            """
        ).fetchall()

    return [
        {
            "group": "Custom",
            "market": row[2] or "Custom / Verified",
            "ticker": row[0],
            "name": row[1] or row[0],
            "asset_type": row[3] or "Custom",
            "exchange": row[4] or "",
            "currency": row[5] or "",
            "source": row[6] or "user_verified"
        }
        for row in rows
    ]


def save_provider_error(provider: str, cache_key: str, error: str):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO provider_errors (
                provider, cache_key, error, cached_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (provider, cache_key, str(error), now_iso())
        )
        connection.commit()
