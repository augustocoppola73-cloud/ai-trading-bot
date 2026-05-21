import os
import pandas as pd
import matplotlib.pyplot as plt

from market_data import download_data
from indicators import add_indicators
from strategy import generate_signals
from backtest import run_backtest
from performance import calculate_performance
from ai_filter import calculate_ai_score
from benchmark import calculate_buy_and_hold
from optimizer import optimize_parameters
from portfolio_scanner import scan_market
from portfolio_engine import build_portfolio_plan
from historical_scanner import scan_market_on_date
from portfolio_backtest import run_portfolio_backtest
from portfolio_performance import calculate_portfolio_performance


if __name__ == "__main__":

    ticker = "SPY"
    initial_capital = 1000

    data = download_data(ticker)

    data = add_indicators(data)

    data = calculate_ai_score(data)

    data = generate_signals(data)

    print("\n====================")
    print("ULTIMI SEGNALI")
    print("====================")

    print(
        data[
            [
                "date",
                "close",
                "ema_20",
                "ema_50",
                "rsi",
                "ai_score",
                "market_regime",
                "signal"
            ]
        ].tail(20)
    )

    results, equity_curve, final_capital = run_backtest(
        data,
        initial_capital=initial_capital
    )

    metrics = calculate_performance(
        trades=results,
        equity_curve=equity_curve,
        initial_capital=initial_capital,
        final_capital=final_capital
    )

    benchmark = calculate_buy_and_hold(
        data,
        initial_capital
    )

    print("\n====================")
    print("TRADES")
    print("====================")
    print(results)

    os.makedirs("reports", exist_ok=True)
    results.to_csv("reports/trades.csv", index=False)
    equity_curve.to_csv("reports/equity_curve.csv", index=False)

    print("\n====================")
    print("PERFORMANCE")
    print("====================")

    for key, value in metrics.items():
        print(f"{key}: {value}")

    print("\n====================")
    print("BUY & HOLD BENCHMARK")
    print("====================")

    for key, value in benchmark.items():
        print(f"{key}: {value}")

    optimization_results = optimize_parameters(
        data,
        initial_capital
    )

    print("\n====================")
    print("OPTIMIZATION RESULTS")
    print("====================")

    print(optimization_results)

    tickers = [
        "SPY",
        "QQQ",
        "AAPL",
        "MSFT",
        "NVDA",
        "BTC-USD",
        "ETH-USD"
    ]

    scanner_results = scan_market(tickers)

    print("\n====================")
    print("MARKET SCANNER")
    print("====================")

    print(scanner_results)

    portfolio_plan, remaining_cash = build_portfolio_plan(
        scanner_results=scanner_results,
        capital=initial_capital,
        top_n=3,
        min_score=120,
        risk_per_trade=0.01,
        atr_multiplier=2.0
    )

    print("\n====================")
    print("PORTFOLIO PLAN")
    print("====================")

    print(portfolio_plan)

    print("\nRemaining Cash:", remaining_cash)

    portfolio_plan.to_csv(
        "reports/portfolio_plan.csv",
        index=False
    )

    historical_scan = scan_market_on_date(
        tickers=tickers,
        scan_date="2024-01-15"
    )

    print("\n====================")
    print("HISTORICAL SCANNER")
    print("====================")

    print(historical_scan)

    portfolio_history, portfolio_final_capital = run_portfolio_backtest(
        tickers=tickers,
        start_date="2023-01-01",
        end_date="2025-12-31",
        initial_capital=1000
    )

    print("\n====================")
    print("PORTFOLIO BACKTEST")
    print("====================")

    print(portfolio_history)

    print("\nFinal Portfolio Capital:", portfolio_final_capital)

    portfolio_history.to_csv(
        "reports/portfolio_backtest.csv",
        index=False
    )

    portfolio_metrics = calculate_portfolio_performance(
        portfolio_history=portfolio_history,
        initial_capital=1000,
        final_capital=portfolio_final_capital
    )

    print("\n====================")
    print("PORTFOLIO PERFORMANCE")
    print("====================")

    for key, value in portfolio_metrics.items():
        print(f"{key}: {value}")

    # ========+++++++========+====
    # SINGLE E MULTI ASSET EQUITY
    # ===============++++++++=====

    plt.figure(figsize=(12, 6))

    plt.plot(
        equity_curve["date"],
        equity_curve["equity"],
        label="Single Asset Strategy"
    )

    plt.plot(
        portfolio_history["scan_date"],
        portfolio_history["capital"],
        label="Multi Asset Portfolio"
    )

    plt.title("Equity Curve Comparison")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")

    plt.legend()
    plt.grid(True)

    plt.show()