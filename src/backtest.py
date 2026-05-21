import pandas as pd

from risk_manager import calculate_position_size_by_risk


def run_backtest(
    df: pd.DataFrame,
    initial_capital: float = 1000,
    atr_multiplier: float = 2.0,
    trailing_atr_multiplier: float = 2.5,
    risk_per_trade: float = 0.01
):

    cash = initial_capital
    position = 0
    entry_price = 0
    stop_loss_price = 0
    trailing_stop_price = 0
    highest_price_since_entry = 0

    trades = []
    equity_curve = []

    for i in range(1, len(df)):

        signal = df.iloc[i]["signal"]
        close_price = df.iloc[i]["close"]
        date = df.iloc[i]["date"]
        atr = df.iloc[i]["atr"]

        position_value = position * close_price
        current_equity = cash + position_value

        equity_curve.append({
            "date": date,
            "equity": current_equity
        })

        # Aggiorna trailing stop se siamo in posizione
        if position > 0:

            if close_price > highest_price_since_entry:
                highest_price_since_entry = close_price

            new_trailing_stop = (
                highest_price_since_entry
                - (atr * trailing_atr_multiplier)
            )

            if new_trailing_stop > trailing_stop_price:
                trailing_stop_price = new_trailing_stop

        active_stop = max(stop_loss_price, trailing_stop_price)

        # USCITA PER STOP
        if position > 0 and close_price <= active_stop:

            sale_value = position * close_price
            cash += sale_value

            pnl = ((close_price - entry_price) / entry_price) * 100

            stop_type = (
                "TRAILING_STOP"
                if active_stop == trailing_stop_price
                else "STOP_LOSS"
            )

            trades.append({
                "date": date,
                "type": stop_type,
                "price": close_price,
                "stop_price": round(active_stop, 2),
                "cash": cash,
                "position_value": 0,
                "equity": cash,
                "pnl_%": round(pnl, 2)
            })

            position = 0
            entry_price = 0
            stop_loss_price = 0
            trailing_stop_price = 0
            highest_price_since_entry = 0

            continue

        # BUY
        if signal == "BUY" and position == 0:

            entry_price = close_price

            stop_loss_price = (
                entry_price
                - (atr * atr_multiplier)
            )

            trailing_stop_price = (
                entry_price
                - (atr * trailing_atr_multiplier)
            )

            allocated_capital = calculate_position_size_by_risk(
                capital=cash,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                risk_per_trade=risk_per_trade
            )

            if allocated_capital > 0:

                position = allocated_capital / close_price
                highest_price_since_entry = close_price

                cash -= allocated_capital

                trades.append({
                    "date": date,
                    "type": "BUY",
                    "price": close_price,
                    "stop_loss": round(stop_loss_price, 2),
                    "trailing_stop": round(trailing_stop_price, 2),
                    "cash": cash,
                    "position_value": allocated_capital,
                    "equity": cash + allocated_capital
                })

        # SELL da segnale strategico
        elif signal == "SELL" and position > 0:

            sale_value = position * close_price
            cash += sale_value

            pnl = ((close_price - entry_price) / entry_price) * 100

            trades.append({
                "date": date,
                "type": "SELL",
                "price": close_price,
                "cash": cash,
                "position_value": 0,
                "equity": cash,
                "pnl_%": round(pnl, 2)
            })

            position = 0
            entry_price = 0
            stop_loss_price = 0
            trailing_stop_price = 0
            highest_price_since_entry = 0

    final_position_value = position * df.iloc[-1]["close"]
    final_capital = cash + final_position_value

    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve)

    return trades_df, equity_df, final_capital