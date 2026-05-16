"""
Phase 1 entry point: fetch holdings for all ETFs in the portfolio.

Usage:
    python -m src.fetch_holdings
    python -m src.fetch_holdings --as-of 2026-05-06

The output is cached to data/holdings/cache/YYYY-MM-DD/.
If any fetcher fails, drop the manual CSV in data/holdings/manual/
and re-run.
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from pathlib import Path

from .fetchers import fetch_all_holdings

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "data" / "config" / "portfolio_weights.xlsx"
CACHE = ROOT / "data" / "holdings" / "cache"
MANUAL = ROOT / "data" / "holdings" / "manual"


def main():
    parser = argparse.ArgumentParser(description="Fetch ETF holdings")
    parser.add_argument(
        "--as-of",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="Snapshot date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Verbose logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    as_of = args.as_of or date.today()
    print(f"\nFetching holdings as of {as_of.isoformat()}...\n")

    holdings = fetch_all_holdings(
        config_path=CONFIG,
        cache_root=CACHE,
        manual_root=MANUAL,
        as_of=as_of,
    )

    print(f"\n{'='*60}")
    print(f"Fetched {len(holdings)} ETFs:")
    for ticker, df in sorted(holdings.items()):
        total_weight = df["Weight (%)"].sum()
        print(f"  {ticker:6s}  {len(df):4d} holdings   sum = {total_weight:6.2f}%")
    print(f"{'='*60}")
    print(f"\nCached to: {CACHE / as_of.isoformat()}")


if __name__ == "__main__":
    main()
