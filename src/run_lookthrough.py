"""
Phase 2 entry point: run look-through analytics and write Excel workbook.

Usage:
    python -m src.run_lookthrough
    python -m src.run_lookthrough --month 2026-05
"""
from __future__ import annotations

import argparse
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .fetchers import fetch_all_holdings
from .lookthrough import run_lookthrough
from .reports.excel_lookthrough import write_lookthrough_excel

ROOT = Path(__file__).resolve().parent.parent
CONFIG  = ROOT / "data" / "config"
CACHE   = ROOT / "data" / "holdings" / "cache"
MANUAL  = ROOT / "data" / "holdings" / "manual"
OUTPUTS = ROOT / "outputs" / "snapshots"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", default=None,
                        help="Report month YYYY-MM (default: current month)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    today = date.today()
    month = args.month or today.strftime("%Y-%m")

    print(f"\n{'='*60}")
    print(f"RH Portfolio Reporting — Look-Through Engine")
    print(f"Month: {month}   |   Run date: {today.isoformat()}")
    print(f"{'='*60}\n")

    # 1. Fetch holdings (always re-fetches fresh per user preference)
    print("Step 1/4 — Fetching ETF holdings...\n")
    # Clear cache for today to force re-fetch
    cache_dir = CACHE / today.isoformat()
    if cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)

    holdings = fetch_all_holdings(
        config_path=CONFIG / "etf_sources.xlsx",
        cache_root=CACHE,
        manual_root=MANUAL,
        as_of=today,
    )

    # 2. Load config files
    print("\nStep 2/4 — Loading configuration...\n")
    portfolio_weights = pd.read_excel(CONFIG / "portfolio_weights.xlsx")
    portfolio_weights = portfolio_weights.dropna(subset=["ETF Ticker"])

    ticker_aliases    = _load_optional(CONFIG / "ticker_aliases.xlsx")
    sector_overrides  = _load_optional(CONFIG / "sector_overrides.xlsx")
    country_overrides = _load_optional(CONFIG / "country_overrides.xlsx")
    report_config     = pd.read_excel(CONFIG / "report_config.xlsx")
    portfolio_name    = _get_config(report_config, "Portfolio Name", "Momentum Global ETF Portfolio")

    # 3. Run look-through
    print("Step 3/4 — Running look-through analytics...\n")
    sheets = run_lookthrough(
        holdings=holdings,
        portfolio_weights=portfolio_weights,
        ticker_aliases=ticker_aliases,
        sector_overrides=sector_overrides,
        country_overrides=country_overrides,
    )

    # 4. Write Excel workbook
    print("Step 4/4 — Writing Excel workbook...\n")
    out_dir = OUTPUTS / month
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "lookthrough.xlsx"

    write_lookthrough_excel(
        sheets=sheets,
        output_path=out_path,
        portfolio_name=portfolio_name,
        as_of=today.strftime("%d %b %Y"),
    )

    # Print summary
    stock_df    = sheets["Stock Look-Through"]
    sector_df   = sheets["Sector Exposure"]
    country_df  = sheets["Country Exposure"]
    summary, top10 = sheets["Concentration"]

    print(f"\n{'='*60}")
    print(f"Look-Through Complete")
    print(f"{'='*60}")
    print(f"  Unique securities:    {len(stock_df)}")
    print(f"  Total weight covered: {stock_df['Portfolio Weight (%)'].sum():.1f}%")
    print(f"\n  Top 5 Sectors:")
    for _, row in sector_df.head(5).iterrows():
        print(f"    {row['Sector']:<28} {row['Portfolio Weight (%)']:>6.2f}%")
    print(f"\n  Top 5 Countries:")
    for _, row in country_df.head(5).iterrows():
        print(f"    {row['Country']:<28} {row['Portfolio Weight (%)']:>6.2f}%")
    print(f"\n  Top 3 Holdings:")
    for _, row in stock_df.head(3).iterrows():
        print(f"    {row['Ticker']:<12} {row['Security Name']:<30} {row['Portfolio Weight (%)']:>5.2f}%")

    quality = sheets["Data Quality"]
    if len(quality) > 0 and quality.iloc[0]["Issue"] != "No data quality issues found":
        print(f"\n  Data quality issues: {len(quality)} (see Data Quality sheet)")

    print(f"\n  Output: {out_path}\n")


def _load_optional(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_excel(path)
    if df.empty or (len(df) == 1 and df.iloc[0].isna().all()):
        return None
    return df


def _get_config(df: pd.DataFrame, key: str, default: str) -> str:
    matches = df[df.iloc[:, 0].astype(str).str.strip() == key]
    if matches.empty:
        return default
    return str(matches.iloc[0, 1]).strip()


if __name__ == "__main__":
    main()
