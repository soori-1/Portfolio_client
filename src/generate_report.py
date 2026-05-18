"""
Right Horizons - Portfolio Report Generator
============================================
Orchestrates the full reporting pipeline:
  1. Fetch holdings (manual CSV -> fetcher -> autodiscover -> synthetic)
  2. Look-through aggregation -> writes lookthrough.xlsx in snapshot dir
  3. Performance metrics (YTD, monthly, best/worst, market exposure)
  4. Export dashboard_data.json -> push to GitHub Pages

PDF generation is intentionally DISABLED on Render (memory limit).
Code preserved in src/reports/pdf_factsheet.py for future re-enable.
"""

from __future__ import annotations

import os
import sys
import shutil
import base64
import traceback
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import requests

# Make src/ importable when run as `python -m src.generate_report`
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.fetch_holdings import fetch_all_holdings
from src.lookthrough import run_lookthrough
from src.performance import run_performance
from src.export_dashboard_data import export as export_dashboard


CONFIG  = ROOT / "data" / "config"
RETURNS = ROOT / "data" / "returns"
OUTPUTS = ROOT / "outputs" / "snapshots"


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _current_month_key() -> str:
    """YYYY-MM for this run's snapshot folder."""
    return date.today().strftime("%Y-%m")


def _write_lookthrough_xlsx(sheets: dict, out_path: Path) -> None:
    """
    run_lookthrough() returns a dict of {sheet_name: DataFrame or tuple}.
    'Concentration' is a (summary_df, top10_df) tuple - stack them.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        for name, payload in sheets.items():
            if isinstance(payload, tuple):
                summary_df, top10_df = payload
                summary_df.to_excel(xw, sheet_name=name, index=False, startrow=0)
                start = len(summary_df) + 2
                top10_df.to_excel(xw, sheet_name=name, index=False, startrow=start)
            else:
                payload.to_excel(xw, sheet_name=name, index=False)


def _push_to_github(local_file: Path, repo_path: str = "dashboard_data.json") -> None:
    """
    Push file to GitHub via Contents API.
    Env: GITHUB_TOKEN, GITHUB_REPO (default soori-1/Portfolio_client),
         GITHUB_BRANCH (default main)
    """
    token  = os.environ.get("GITHUB_TOKEN")
    repo   = os.environ.get("GITHUB_REPO", "soori-1/Portfolio_client")
    branch = os.environ.get("GITHUB_BRANCH", "main")

    if not token:
        raise RuntimeError("GITHUB_TOKEN not set")

    api = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Need current SHA to update (404 = new file, no SHA needed)
    sha = None
    r = requests.get(api, headers=headers, params={"ref": branch}, timeout=30)
    if r.status_code == 200:
        sha = r.json().get("sha")
    elif r.status_code != 404:
        r.raise_for_status()

    payload = {
        "message": f"Update dashboard_data.json [{datetime.now().strftime('%Y-%m-%d %H:%M')}]",
        "content": base64.b64encode(local_file.read_bytes()).decode("ascii"),
        "branch":  branch,
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(api, headers=headers, json=payload, timeout=30)
    r.raise_for_status()


def main() -> int:
    log("=" * 60)
    log("RIGHT HORIZONS - PORTFOLIO REPORT GENERATION")
    log("=" * 60)

    month_key = _current_month_key()
    snapshot_dir = OUTPUTS / month_key
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    log(f"Snapshot dir: {snapshot_dir}")

    # ── Step 1: Fetch holdings ────────────────────────────────────
    log("STEP 1/4 - Fetching holdings for all ETFs")
    try:
        holdings = fetch_all_holdings()
        if not holdings:
            log("ERROR: No holdings returned")
            return 1
        log(f"  OK - Holdings fetched for {len(holdings)} ETFs")
    except Exception as e:
        log(f"ERROR in fetch_holdings: {e}")
        traceback.print_exc()
        return 1

    # ── Step 2: Look-through aggregation ──────────────────────────
    log("STEP 2/4 - Building look-through (stocks, sectors, countries)")
    try:
        portfolio_weights = pd.read_excel(CONFIG / "portfolio_weights.xlsx").dropna(subset=["ETF Ticker"])

        def _optional(p: Path):
            return pd.read_excel(p) if p.exists() else None

        sheets = run_lookthrough(
            holdings          = holdings,
            portfolio_weights = portfolio_weights,
            ticker_aliases    = _optional(CONFIG / "ticker_aliases.xlsx"),
            sector_overrides  = _optional(CONFIG / "sector_overrides.xlsx"),
            country_overrides = _optional(CONFIG / "country_overrides.xlsx"),
        )

        lt_path = snapshot_dir / "lookthrough.xlsx"
        _write_lookthrough_xlsx(sheets, lt_path)
        log(f"  OK - lookthrough.xlsx -> {lt_path.name}")
    except Exception as e:
        log(f"ERROR in lookthrough: {e}")
        traceback.print_exc()
        return 1

    # ── Step 3: Performance metrics ───────────────────────────────
    log("STEP 3/4 - Computing performance metrics")
    try:
        perf = run_performance(
            monthly_returns_path    = RETURNS / "monthly_returns.xlsx",
            etf_performance_path    = RETURNS / "etf_monthly_performance.xlsx",
            etf_classification_path = CONFIG  / "etf_classification.xlsx",
            portfolio_weights_path  = CONFIG  / "portfolio_weights.xlsx",
        )
        mt = perf.get("monthly_table")
        if mt is not None and len(mt):
            ytd = mt[mt["Month"] == "YTD"]
            if len(ytd):
                p = ytd["Portfolio (%)"].iloc[0]
                b = ytd["Benchmark (%)"].iloc[0]
                log(f"  OK - YTD portfolio: {p}%  |  benchmark: {b}%")
    except Exception as e:
        log(f"ERROR in performance: {e}")
        traceback.print_exc()
        return 1

    # ── Step 4: Export dashboard data + push to GitHub ────────────
    log("STEP 4/4 - Exporting dashboard_data.json")
    try:
        # export() picks the latest snapshot automatically
        snap_json = export_dashboard()

        # Copy to repo root (GitHub Pages serves from /)
        root_json = ROOT / "dashboard_data.json"
        shutil.copy(snap_json, root_json)
        log(f"  OK - dashboard_data.json -> repo root")
    except Exception as e:
        log(f"ERROR in export_dashboard: {e}")
        traceback.print_exc()
        return 1

    # Push to GitHub Pages
    if os.environ.get("GITHUB_TOKEN"):
        log("       Pushing dashboard_data.json to GitHub Pages")
        try:
            _push_to_github(root_json, repo_path="dashboard_data.json")
            log("  OK - Pushed - live dashboard refreshes in ~60s")
        except Exception as e:
            log(f"WARN: GitHub push failed: {e}")
            traceback.print_exc()
    else:
        log("  -- GITHUB_TOKEN not set - skipping push (local-only run)")

    log("=" * 60)
    log("DONE - REPORT GENERATION COMPLETE")
    log("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
