"""
Right Horizons - Portfolio Report Generator
============================================
Orchestrates the full reporting pipeline:
  1. Fetch holdings (manual CSV → fetcher → autodiscover → synthetic)
  2. Look-through aggregation (stock-level, GICS, country)
  3. Performance metrics (YTD, monthly, best/worst, exposure)
  4. Export dashboard_data.json → push to GitHub Pages

PDF generation is intentionally DISABLED on Render (memory limit).
Code preserved in src/reports/pdf_factsheet.py for future re-enable.
"""

import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime

# Make src/ importable when run as `python -m src.generate_report`
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.fetch_holdings import fetch_all_holdings
from src.lookthrough import build_lookthrough
from src.performance import compute_performance
from src.export_dashboard_data import export_dashboard, push_to_github


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def main() -> int:
    log("=" * 60)
    log("RIGHT HORIZONS — PORTFOLIO REPORT GENERATION")
    log("=" * 60)

    # ── Step 1: Fetch holdings ────────────────────────────────────
    log("STEP 1/4 — Fetching holdings for all ETFs")
    try:
        holdings = fetch_all_holdings()
        if not holdings:
            log("ERROR: No holdings returned")
            return 1
        log(f"  ✓ Holdings fetched for {len(holdings)} ETFs")
    except Exception as e:
        log(f"ERROR in fetch_holdings: {e}")
        traceback.print_exc()
        return 1

    # ── Step 2: Look-through aggregation ──────────────────────────
    log("STEP 2/4 — Building look-through (stocks, sectors, countries)")
    try:
        lookthrough = build_lookthrough(holdings)
        log(f"  ✓ {len(lookthrough.get('stocks', []))} unique stocks aggregated")
        log(f"  ✓ {len(lookthrough.get('sectors', {}))} sectors")
        log(f"  ✓ {len(lookthrough.get('countries', {}))} countries")
    except Exception as e:
        log(f"ERROR in lookthrough: {e}")
        traceback.print_exc()
        return 1

    # ── Step 3: Performance metrics ───────────────────────────────
    log("STEP 3/4 — Computing performance metrics")
    try:
        perf = compute_performance()
        log(f"  ✓ YTD return: {perf.get('ytd_return', 'n/a')}")
        log(f"  ✓ MTD return: {perf.get('mtd_return', 'n/a')}")
    except Exception as e:
        log(f"ERROR in performance: {e}")
        traceback.print_exc()
        return 1

    # ── Step 4: Export dashboard data + push to GitHub ────────────
    log("STEP 4/4 — Exporting dashboard_data.json")
    try:
        out_path = export_dashboard(holdings, lookthrough, perf)
        log(f"  ✓ Written: {out_path}")
    except Exception as e:
        log(f"ERROR in export_dashboard: {e}")
        traceback.print_exc()
        return 1

    # Push to GitHub (Pages auto-rebuilds in ~60s)
    if os.environ.get("GITHUB_TOKEN"):
        log("       Pushing dashboard_data.json to GitHub Pages")
        try:
            push_to_github(out_path)
            log("  ✓ Pushed — live dashboard will refresh in ~60s")
        except Exception as e:
            log(f"WARN: GitHub push failed: {e}")
            traceback.print_exc()
    else:
        log("  ⊘ GITHUB_TOKEN not set — skipping push (local-only run)")

    log("=" * 60)
    log("✓ REPORT GENERATION COMPLETE")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
