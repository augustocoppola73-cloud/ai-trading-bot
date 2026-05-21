import argparse
import os
from pathlib import Path

from market_universe import (
    get_assets_for_market,
    get_market_names
)
from paper_trading import run_daily_paper_trading


# Ensure working directory is project root so reports/ is correct.
os.chdir(Path(__file__).resolve().parent.parent)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run daily paper trading scanner."
    )
    parser.add_argument(
        "--market",
        type=str,
        default="Italy - Borsa Italiana",
        help="Market name from the universe catalog."
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=120
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    available_markets = get_market_names()

    if args.market not in available_markets:
        print(f"Mercato '{args.market}' non trovato.")
        print(f"Disponibili: {available_markets}")
        raise SystemExit(1)

    tickers = get_assets_for_market(args.market)
    print(f"Mercato: {args.market}")
    print(f"Ticker caricati: {len(tickers)}")

    scanner, portfolio_plan, summary = run_daily_paper_trading(
        tickers=tickers,
        capital=args.capital,
        top_n=args.top_n,
        min_score=args.min_score,
        risk_per_trade=0.01,
        atr_multiplier=2.0,
        market=args.market
    )

    print("\n====================")
    print("LIVE SCANNER")
    print("====================")
    print(scanner)

    print("\n====================")
    print("PAPER PORTFOLIO PLAN")
    print("====================")
    print(portfolio_plan)

    print("\n====================")
    print("SUMMARY")
    print("====================")
    print(summary)