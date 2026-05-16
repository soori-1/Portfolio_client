"""
Master report runner — generates the full monthly factsheet.

Usage:
    python -m src.generate_report
    python -m src.generate_report --month 2026-05
"""
from __future__ import annotations

import argparse
import shutil
from datetime import date
from pathlib import Path

import pandas as pd

from .fetchers import fetch_all_holdings
from .lookthrough import run_lookthrough
from .performance import run_performance
from .reports.pdf_factsheet import generate_factsheet
from .export_dashboard_data import export as export_dashboard

ROOT    = Path(__file__).resolve().parent.parent
CONFIG  = ROOT / "data" / "config"
CACHE   = ROOT / "data" / "holdings" / "cache"
MANUAL  = ROOT / "data" / "holdings" / "manual"
RETURNS = ROOT / "data" / "returns"
OUTPUTS = ROOT / "outputs" / "snapshots"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", default=None,
                        help="YYYY-MM (default: current month)")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip re-fetching holdings (use cache)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    today = date.today()
    month = args.month or today.strftime("%Y-%m")
    month_label = pd.to_datetime(month + "-01").strftime("%B %Y")
    ref_date = today.strftime("%d %B %Y")

    print(f"\n{'='*60}")
    print(f"RH Portfolio Reporting — Generate Report")
    print(f"Month: {month_label}   |   Run date: {today.isoformat()}")
    print(f"{'='*60}\n")

    # Load config
    portfolio_weights = pd.read_excel(CONFIG / "portfolio_weights.xlsx").dropna(subset=["ETF Ticker"])
    report_cfg = pd.read_excel(CONFIG / "report_config.xlsx")

    def cfg(key, default=""):
        m = report_cfg[report_cfg.iloc[:, 0].astype(str).str.strip() == key]
        return str(m.iloc[0, 1]).strip() if not m.empty else default

    portfolio_name = cfg("Portfolio Name", "Momentum Global ETF Portfolio")
    benchmark_name = cfg("Benchmark Name", "MSCI ACWI")
    company_name   = cfg("Company Name",   "Right Horizons Wealth Management")
    tagline        = cfg("Report Tagline", "Guiding you in achieving your goals")
    n_holdings     = int(cfg("Number of Holdings", len(portfolio_weights)))

    # Step 1 — Fetch holdings
    print("Step 1/4 — Fetching holdings...\n")
    force_refresh = not args.skip_fetch

    holdings = fetch_all_holdings(
        config_path=CONFIG / "portfolio_weights.xlsx",
        cache_root=CACHE,
        manual_root=MANUAL,
        as_of=today,
        force_refresh=force_refresh,
    )

    # Step 2 — Look-through
    print("\nStep 2/4 — Running look-through...\n")
    ticker_aliases    = _load_opt(CONFIG / "ticker_aliases.xlsx")
    sector_overrides  = _load_opt(CONFIG / "sector_overrides.xlsx")
    country_overrides = _load_opt(CONFIG / "country_overrides.xlsx")

    lookthrough_sheets = run_lookthrough(
        holdings=holdings,
        portfolio_weights=portfolio_weights,
        ticker_aliases=ticker_aliases,
        sector_overrides=sector_overrides,
        country_overrides=country_overrides,
    )

    # Step 3 — Performance
    print("Step 3/4 — Running performance engine...\n")
    performance = run_performance(
        monthly_returns_path    = RETURNS / "monthly_returns.xlsx",
        etf_performance_path    = RETURNS / "etf_monthly_performance.xlsx",
        etf_classification_path = CONFIG  / "etf_classification.xlsx",
        portfolio_weights_path  = CONFIG  / "portfolio_weights.xlsx",
    )

    # Step 4 — Generate PDF
    print("Step 4/4 — Generating PDF factsheet...\n")
    out_dir = OUTPUTS / month
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"RH_MomentumGlobal_{month}.pdf"

    commentary_path = ROOT / "data" / "commentary" / f"{month}.md"
    disclaimer_path = CONFIG / "disclaimer.txt"

    generate_factsheet(
        output_path    = pdf_path,
        performance    = performance,
        lookthrough_sheets = lookthrough_sheets,
        report_month   = month_label,
        reference_date = ref_date,
        n_holdings     = n_holdings,
        portfolio_name = portfolio_name,
        benchmark_name = benchmark_name,
        company_name   = company_name,
        tagline        = tagline,
        commentary_path = commentary_path,
        disclaimer_path = disclaimer_path,
    )

    print(f"\n{'='*60}")
    print(f"Report generated successfully!")
    print(f"  PDF:  {pdf_path}")
    print(f"{'='*60}\n")


def _load_opt(path):
    if not path.exists():
        return None
    df = pd.read_excel(path)
    return df if not df.empty else None


if __name__ == "__main__":
    main()
