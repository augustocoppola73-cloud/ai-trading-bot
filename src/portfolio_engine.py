import pandas as pd

from risk_manager import calculate_position_size_by_risk


def get_paper_trading_decision_reason(
    row,
    min_score: float
) -> str:

    if row["scanner_score"] < min_score:
        return "EXCLUDED_SCORE_BELOW_MINIMUM"

    if row["market_regime"] != "BULL":
        return "EXCLUDED_MARKET_REGIME_NOT_BULL"

    if row["signal"] != "BUY":
        return "EXCLUDED_SIGNAL_NOT_BUY"

    if pd.isna(row["close"]) or row["close"] <= 0:
        return "EXCLUDED_INVALID_CLOSE_PRICE"

    if pd.isna(row["atr"]) or row["atr"] <= 0:
        return "EXCLUDED_INVALID_ATR"

    return "INCLUDED_VALID_BUY_SETUP"


def build_paper_decision_log(
    scanner_results: pd.DataFrame,
    min_score: float = 120
) -> pd.DataFrame:

    if scanner_results is None or scanner_results.empty:
        return pd.DataFrame(
            columns=[
                "ticker",
                "scanner_score",
                "market_regime",
                "signal",
                "position_status",
                "decision_reason"
            ]
        )

    decision_log = scanner_results.copy()

    decision_log["decision_reason"] = decision_log.apply(
        lambda row: get_paper_trading_decision_reason(
            row=row,
            min_score=min_score
        ),
        axis=1
    )

    decision_log["position_status"] = decision_log["decision_reason"].apply(
        lambda reason: "CANDIDATE"
        if reason == "INCLUDED_VALID_BUY_SETUP"
        else "EXCLUDED"
    )

    return decision_log


def build_portfolio_plan(
    scanner_results: pd.DataFrame,
    capital: float = 1000,
    top_n: int = 3,
    min_score: float = 120,
    risk_per_trade: float = 0.01,
    atr_multiplier: float = 2.0,
    trailing_atr_multiplier: float = 2.5,
    return_decision_log: bool = False
):

    decision_log = build_paper_decision_log(
        scanner_results=scanner_results,
        min_score=min_score
    )

    candidates = decision_log[
        decision_log["decision_reason"] == "INCLUDED_VALID_BUY_SETUP"
    ].copy()

    candidates = candidates.head(top_n)

    if candidates.empty:
        empty_plan = pd.DataFrame()

        if return_decision_log:
            return empty_plan, capital, decision_log

        return empty_plan, capital

    portfolio_rows = []
    remaining_cash = capital

    for _, row in candidates.iterrows():

        entry_price = row["close"]
        atr = row["atr"]

        stop_loss_price = entry_price - (atr * atr_multiplier)

        trailing_stop_price = entry_price - (atr * trailing_atr_multiplier)

        allocated_capital = calculate_position_size_by_risk(
            capital=remaining_cash,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            risk_per_trade=risk_per_trade
        )

        allocated_capital = min(allocated_capital, remaining_cash)

        if allocated_capital <= 0:
            decision_log.loc[
                decision_log["ticker"] == row["ticker"],
                ["position_status", "decision_reason"]
            ] = [
                "EXCLUDED",
                "EXCLUDED_INSUFFICIENT_CAPITAL"
            ]
            continue

        estimated_quantity = allocated_capital / entry_price

        stop_distance_pct = (
            (entry_price - stop_loss_price)
            / entry_price
        )

        estimated_max_loss = allocated_capital * stop_distance_pct

        remaining_cash -= allocated_capital
        risk_pct = (
            (estimated_max_loss / capital) * 100
            if capital > 0
            else 0
        )

        portfolio_rows.append({
            "ticker": row["ticker"],
            "scanner_score": row["scanner_score"],
            "market_regime": row["market_regime"],
            "signal": row["signal"],
            "position_status": "SELECTED",
            "decision_reason": "SELECTED_VALID_BUY_SETUP",
            "entry_price": round(entry_price, 2),
            "atr": round(atr, 4),
            "stop_loss_price": round(stop_loss_price, 2),
            "initial_trailing_stop": round(trailing_stop_price, 2),
            "risk_per_trade_%": risk_per_trade * 100,
            "risk_$": round(estimated_max_loss, 2),
            "risk_%": round(risk_pct, 2),
            "capital_allocation_%": round((allocated_capital / capital) * 100, 2),
            "capital_allocation_$": round(allocated_capital, 2),
            "estimated_quantity": round(estimated_quantity, 4),
            "estimated_max_loss_$": round(estimated_max_loss, 2)
        })

        decision_log.loc[
            decision_log["ticker"] == row["ticker"],
            ["position_status", "decision_reason"]
        ] = [
            "SELECTED",
            "SELECTED_VALID_BUY_SETUP"
        ]

    portfolio_df = pd.DataFrame(portfolio_rows)

    if return_decision_log:
        return portfolio_df, round(remaining_cash, 2), decision_log

    return portfolio_df, round(remaining_cash, 2)
