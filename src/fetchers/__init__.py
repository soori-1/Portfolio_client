"""
Holdings fetcher router.

Cache strategy: use any cache from the CURRENT MONTH — don't re-fetch
if we already have this month's holdings. Only fetch fresh if cache is
from a previous month or missing entirely.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from .ishares import fetch_ishares
from .vanguard import fetch_vanguard
from .globalx import fetch_globalx

log = logging.getLogger(__name__)

FETCHERS = {
    "ishares": fetch_ishares,
    "vanguard": fetch_vanguard,
    "globalx": fetch_globalx,
}


def fetch_all_holdings(
    config_path: Path,
    cache_root: Path,
    manual_root: Path,
    as_of: Optional[date] = None,
    force_refresh: bool = False,
) -> dict[str, pd.DataFrame]:
    as_of = as_of or date.today()

    # Use any cache from this calendar month — iShares blocks frequent re-fetches
    cache_dir = _find_or_create_cache_dir(cache_root, as_of, force_refresh)

    sources = pd.read_excel(config_path)
    results: dict[str, pd.DataFrame] = {}
    errors:  dict[str, str] = {}

    for _, row in sources.iterrows():
        ticker      = str(row["Ticker"]).strip()
        issuer      = str(row["Issuer"]).strip().lower()
        product_url = row.get("Product URL")
        if pd.isna(product_url):
            product_url = None

        try:
            df = _fetch_one(ticker, issuer, product_url, cache_dir, manual_root)
            results[ticker] = df
            print(f"  OK  {ticker:6s}  {len(df):4d} holdings")
        except Exception as e:
            errors[ticker] = str(e)
            print(f"  ERR {ticker:6s}  {e}")

    if errors:
        lines = ["\nFailed:"]
        for t, e in errors.items():
            lines.append(f"  {t}: {e}")
        lines.append(f"\nDrop manual CSVs in {manual_root} and re-run.")
        raise RuntimeError("\n".join(lines))

    return results


def _find_or_create_cache_dir(cache_root: Path, as_of: date, force_refresh: bool) -> Path:
    """
    Return the best cache directory for this run.

    Priority:
      1. Today's cache dir (if it has files)
      2. Any other cache dir from the same calendar month
      3. Create today's cache dir fresh (will trigger fetches)
    """
    today_dir = cache_root / as_of.isoformat()

    if force_refresh:
        import shutil
        if today_dir.exists():
            shutil.rmtree(today_dir)
        today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    # Check today's dir
    if today_dir.exists() and any(today_dir.glob("*.csv")):
        return today_dir

    # Look for any cache from same month (e.g. 2026-05-11 when today is 2026-05-16)
    month_prefix = as_of.strftime("%Y-%m")
    if cache_root.exists():
        candidates = sorted(
            [d for d in cache_root.iterdir()
             if d.is_dir() and d.name.startswith(month_prefix) and any(d.glob("*.csv"))],
            reverse=True  # most recent first
        )
        if candidates:
            best = candidates[0]
            print(f"  (using cached holdings from {best.name})")
            # Symlink or copy to today's dir so future runs find it quickly
            today_dir.mkdir(parents=True, exist_ok=True)
            import shutil
            for f in best.glob("*.csv"):
                dst = today_dir / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
            return today_dir

    today_dir.mkdir(parents=True, exist_ok=True)
    return today_dir


def _fetch_one(ticker, issuer, product_url, cache_dir, manual_root):
    cached = cache_dir / f"{ticker}.csv"
    if cached.exists():
        return _load_standardized(cached)

    manual = manual_root / f"{ticker}.csv"

    if issuer == "manual":
        if manual.exists():
            df = _load_standardized(manual)
            df.to_csv(cached, index=False)
            return df
        raise RuntimeError(f"manual upload needed at {manual}")

    if issuer in FETCHERS:
        try:
            print(f"       fetching from {issuer}...")
            df = FETCHERS[issuer](ticker=ticker, product_url=product_url)
            df = _standardize(df)
            df.to_csv(cached, index=False)
            return df
        except Exception as e:
            print(f"       fetch error: {e}")
            if manual.exists():
                print(f"       using manual fallback")
                df = _load_standardized(manual)
                df.to_csv(cached, index=False)
                return df
            raise RuntimeError(f"fetch error: {e}") from e

    if manual.exists():
        return _load_standardized(manual)

    raise RuntimeError(f"unknown issuer '{issuer}', no manual at {manual}")


REQUIRED_COLS = ["Ticker", "Security Name", "Weight (%)"]
OPTIONAL_COLS = ["Sector", "Country", "Asset Class"]


def _standardize(df):
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    for c in OPTIONAL_COLS:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[REQUIRED_COLS + OPTIONAL_COLS]
    df["Weight (%)"] = pd.to_numeric(df["Weight (%)"], errors="coerce")
    df = df.dropna(subset=["Ticker", "Weight (%)"])
    df = df[df["Weight (%)"] > 0]
    return df.reset_index(drop=True)


def _load_standardized(path):
    return _standardize(pd.read_csv(path))