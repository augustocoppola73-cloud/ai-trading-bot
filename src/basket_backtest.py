import pandas as pd

from market_data import download_data


def run_static_basket_backtest(
    tickers: list,
    start_date: str,
    end_date: str,
    initial_capital: float = 1000
):
    """
    Backtest buy & hold equally weighted su paniere statico.
    """

    if not tickers:
        return pd.DataFrame(), initial_capital

    allocation_per_asset = initial_capital / len(tickers)
    basket_curves = []

    for ticker in tickers:
        try:
            data = download_data(ticker)

            data = data[
                (data["date"] >= start_date) &
                (data["date"] <= end_date)
            ].copy()

            if data.empty:
                continue

            first_price = data.iloc[0]["close"]
            shares = allocation_per_asset / first_price

            data["asset_value"] = data["close"] * shares
            data["ticker"] = ticker

            basket_curves.append(
                data[["date", "ticker", "asset_value"]]
            )

        except Exception as e:
            print(f"Errore basket {ticker}: {e}")

    if not basket_curves:
        return pd.DataFrame(), initial_capital

    all_data = pd.concat(basket_curves)

    basket_history = all_data.pivot_table(
        index="date",
        columns="ticker",
        values="asset_value",
        aggfunc="last"
    ).ffill()

    basket_history["capital"] = basket_history.sum(axis=1)

    basket_history = basket_history.reset_index()

    basket_history = basket_history[["date", "capital"]].copy()

    basket_history["weekly_return_%"] = (
        basket_history["capital"].pct_change().fillna(0) * 100
    )

    final_capital = basket_history["capital"].iloc[-1]

    return basket_history, round(final_capital, 2)