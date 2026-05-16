"""
Vanguard holdings fetcher — direct CSV download, no etf-scraper needed.

Vanguard publishes holdings at:
  https://advisors.vanguard.com/investments/products/{FUND_ID}/portfolio
with a CSV download link on the page.

For VT specifically the direct CSV URL is known and stable.
"""
from __future__ import annotations

import logging
import re
from io import StringIO
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

# Direct CSV URL for VT
VANGUARD_URLS = {
    "VT": "https://advisors.vanguard.com/investments/products/0968/vanguard-total-world-stock-etf/portfolio/holdings-export?type=csv",
}

# Fallback: scrape the fund page for the CSV link
VANGUARD_FUND_PAGES = {
    "VT": "https://investor.vanguard.com/etf/profile/portfolio/VT/portfolio-holdings",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
}
TIMEOUT = 30


def fetch_vanguard(ticker: str, product_url: Optional[str] = None) -> pd.DataFrame:
    url = VANGUARD_URLS.get(ticker)
    if url is None:
        raise ValueError(f"No Vanguard URL configured for {ticker}")

    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    df = _parse_vanguard_csv(response.text, ticker)
    return df


def _parse_vanguard_csv(text: str, ticker: str) -> pd.DataFrame:
    """
    Vanguard CSV may have metadata rows at the top.
    We scan for the header row containing holding name / weight columns.
    """
    lines = text.splitlines()
    header_idx = None

    for i, line in enumerate(lines):
        cols = [c.strip().strip('"').lower() for c in line.split(",")]
        if len(cols) >= 3 and any(
            c in cols for c in ["ticker", "holding name", "% of funds", "% of fund"]
        ):
            header_idx = i
            break

    if header_idx is None:
        # Try parsing the whole thing — sometimes Vanguard has no preamble
        try:
            df = pd.read_csv(StringIO(text))
            df.columns = [c.strip() for c in df.columns]
            return _rename_vanguard(df)
        except Exception as e:
            raise ValueError(
                f"Could not parse Vanguard CSV for {ticker}: {e}"
            )

    data_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(StringIO(data_text))
    df.columns = [c.strip() for c in df.columns]
    return _rename_vanguard(df)


def _rename_vanguard(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Holding Name":    "Security Name",
        "% of Funds":      "Weight (%)",
        "% of Fund":       "Weight (%)",
        "% of net assets": "Weight (%)",
        "Name":            "Security Name",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})