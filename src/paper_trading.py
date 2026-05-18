import os
import json
from datetime import datetime
import pandas as pd

from market_universe import get_assets_for_market
from portfolio_scanner import scan_market
from portfolio_engine import build_portfolio_plan


def normalize_report_name(value: str) -> str:
    return (
        value
        .lower()
        .replace("&", "and")
        .replace(" ", "_")
        .replace("/", "_")
    )


def build_run_manifest(
    run_id: str,
    run_date: str,
    market: str,
    tickers: list,
    parameters: dict,
    generated_files: dict
) -> dict:

    return {
        "run_id": run_id,
        "run_date": run_date,
        "market": market,
        "universe_size": len(tickers),
        "tickers": tickers,
        "parameters": parameters,
        "generated_files": generated_files
    }


def run_daily_paper_trading(
    tickers: list,
    capital: float = 1000,
    top_n: int = 3,
    min_score: float = 120,
    risk_per_trade: float = 0.01,
    atr_multiplier: float = 2.0,
    market: str = "Custom",
    strategy_config: dict | None = None
):

    scanner_results = scan_market(tickers, strategy_config=strategy_config)

    portfolio_plan, remaining_cash, decision_log = build_portfolio_plan(
        scanner_results=scanner_results,
        capital=capital,
        top_n=top_n,
        min_score=min_score,
        risk_per_trade=risk_per_trade,
        atr_multiplier=atr_multiplier,
        return_decision_log=True
    )

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    run_id = now.strftime("%Y%m%d_%H%M%S")
    market_slug = normalize_report_name(market)

    os.makedirs("reports", exist_ok=True)

    generated_files = {
        "scanner": f"reports/live_scanner_{today}.csv",
        "portfolio_plan": f"reports/paper_portfolio_plan_{today}.csv",
        "summary": f"reports/paper_summary_{today}.csv",
        "decision_log": f"reports/paper_decision_log_{today}.csv",
        "run_manifest": f"reports/run_manifest_{today}.json",
        "universe_snapshot": (
            f"reports/universe_snapshot_{market_slug}_{today}.csv"
        )
    }

    scanner_results.to_csv(generated_files["scanner"], index=False)
    portfolio_plan.to_csv(generated_files["portfolio_plan"], index=False)
    decision_log.to_csv(generated_files["decision_log"], index=False)

    universe_snapshot = pd.DataFrame({
        "run_id": run_id,
        "date": today,
        "market": market,
        "ticker": tickers
    })

    universe_snapshot.to_csv(
        generated_files["universe_snapshot"],
        index=False
    )

    invested_capital = capital - remaining_cash
    cash_pct = (remaining_cash / capital) * 100 if capital > 0 else 0
    exposure_pct = (invested_capital / capital) * 100 if capital > 0 else 0

    summary = {
        "run_id": run_id,
        "date": today,
        "market": market,
        "capital": capital,
        "remaining_cash": remaining_cash,
        "invested_capital": capital - remaining_cash,
        "cash_%": round(cash_pct, 2),
        "exposure_%": round(exposure_pct, 2),
        "positions": len(portfolio_plan),
        "top_n": top_n,
        "min_score": min_score,
        "risk_per_trade_%": risk_per_trade * 100,
        "atr_multiplier": atr_multiplier,
        "generated_files": json.dumps(generated_files)
    }

    summary_df = pd.DataFrame([summary])

    summary_df.to_csv(generated_files["summary"], index=False)

    manifest = build_run_manifest(
        run_id=run_id,
        run_date=today,
        market=market,
        tickers=tickers,
        parameters={
            "capital": capital,
            "top_n": top_n,
            "min_score": min_score,
            "risk_per_trade": risk_per_trade,
            "atr_multiplier": atr_multiplier
        },
        generated_files=generated_files
    )

    with open(generated_files["run_manifest"], "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2)

    return scanner_results, portfolio_plan, summary_df


def run_paper_trading_for_market(
    market_name: str,
    capital: float = 1000,
    top_n: int = 3,
    min_score: float = 120,
    risk_per_trade: float = 0.01,
    atr_multiplier: float = 2.0,
    strategy_config: dict | None = None
):

    tickers = get_assets_for_market(market_name)

    return run_daily_paper_trading(
        tickers=tickers,
        capital=capital,
        top_n=top_n,
        min_score=min_score,
        risk_per_trade=risk_per_trade,
        atr_multiplier=atr_multiplier,
        market=market_name,
        strategy_config=strategy_config
    )


def run_paper_trading_for_tickers(
    tickers: list,
    market_label: str = "Custom",
    capital: float = 1000,
    top_n: int = 3,
    min_score: float = 120,
    risk_per_trade: float = 0.01,
    atr_multiplier: float = 2.0,
    strategy_config: dict | None = None
):

    return run_daily_paper_trading(
        tickers=tickers,
        capital=capital,
        top_n=top_n,
        min_score=min_score,
        risk_per_trade=risk_per_trade,
        atr_multiplier=atr_multiplier,
        market=market_label,
        strategy_config=strategy_config
    )
