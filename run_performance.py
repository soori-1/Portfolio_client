"""
Phase 3 entry point: run performance engine.

Usage:
    python -m src.run_performance
    python -m src.run_performance --month 2026-05
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .performance import run_performance

ROOT    = Path(__file__).resolve().parent.parent
CONFIG  = ROOT / "data" / "config"
RETURNS = ROOT / "data" / "returns"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", default=None)
    args = parser.parse_args()

    print("\nRH Portfolio Reporting — Performance Engine\n")

    results = run_performance(
        monthly_returns_path    = RETURNS / "monthly_returns.xlsx",
        etf_performance_path    = RETURNS / "etf_monthly_performance.xlsx",
        etf_classification_path = CONFIG  / "etf_classification.xlsx",
        portfolio_weights_path  = CONFIG  / "portfolio_weights.xlsx",
    )

    # ── Monthly table ──
    print("Monthly Performance vs Benchmark")
    print("─" * 62)
    table = results["monthly_table"]
    for _, row in table.iterrows():
        port  = row["Portfolio (%)"]
        bench = row["Benchmark (%)"]
        out   = row["Outperformance (%)"]
        label = row["Month Label"]
        sign  = lambda v: f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"
        print(f"  {label:<18}  Port: {sign(port):>8}  ACWI: {sign(bench):>8}  Alpha: {sign(out):>8}")

    # ── Best / Worst ──
    bw = results["best_worst"]
    print("\nTop Gainers (May 2026):")
    for e in bw["gainers"]:
        print(f"  {e['ticker']:<6}  {e['name']:<45}  {e['return']:+.2f}%")
    print("\nLaggards (May 2026):")
    for e in bw["laggards"]:
        print(f"  {e['ticker']:<6}  {e['name']:<45}  {e['return']:+.2f}%")

    # ── Market exposure ──
    me = results["market_exposure"]
    print("\nMarket Exposure:")
    for k, v in me["by_market"].items():
        print(f"  {k:<25}  {v:.1f}%")
    print("\nETF Type:")
    for k, v in me["by_type"].items():
        print(f"  {k:<25}  {v:.1f}%")

    print("\nPerformance engine OK.\n")


if __name__ == "__main__":
    main()
