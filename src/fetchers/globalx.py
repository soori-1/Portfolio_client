"""
Global X holdings fetcher.

Global X CSVs have metadata rows at the top before the actual data starts.
We skip rows until we find the header row containing "Ticker" or "Name".
"""
from __future__ import annotations

import logging
import re
from io import StringIO
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

BASE_URL = "https://www.globalxetfs.com/funds/{ticker}/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
TIMEOUT = 30


def fetch_globalx(ticker: str, product_url: Optional[str] = None) -> pd.DataFrame:
    if product_url is None:
        product_url = BASE_URL.format(ticker=ticker.lower())

    csv_url = _find_holdings_csv_url(product_url)
    log.debug("CSV URL for %s: %s", ticker, csv_url)

    response = requests.get(csv_url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()

    df = _parse_globalx_csv(response.text)

    rename_map = {
        "Name":           "Security Name",
        "Fund Name":      "Security Name",
        "Weight":         "Weight (%)",
        "Net Assets (%)": "Weight (%)",
        "% of Net Assets": "Weight (%)",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    return df


def _parse_globalx_csv(text: str) -> pd.DataFrame:
    """
    Global X CSVs look like:
        Fund Name,Global X Hydrogen ETF
        As of Date,05/09/2026
        
        Ticker,Name,SEDOL,...
        PLUG,Plug Power Inc,...

    We scan lines until we find the header row (contains 'Ticker' or 'Name'),
    then parse from there.
    """
    lines = text.splitlines()
    header_idx = None

    for i, line in enumerate(lines):
        # Header row has multiple comma-separated fields and contains
        # common column names
        cols = [c.strip().lower() for c in line.split(",")]
        if len(cols) >= 3 and any(
            c in cols for c in ["ticker", "name", "weight", "net assets (%)"]
        ):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(
            "Could not find header row in Global X CSV. "
            "Column names may have changed — check the raw CSV."
        )

    data_text = "\n".join(lines[header_idx:])
    df = pd.read_csv(StringIO(data_text))
    df.columns = [c.strip() for c in df.columns]
    return df


def _find_holdings_csv_url(product_url: str) -> str:
    response = requests.get(product_url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    html = response.text

    matches = re.findall(
        r'href="([^"]*holdings[^"]*\.csv[^"]*)"',
        html,
        flags=re.IGNORECASE,
    )

    if not matches:
        raise RuntimeError(
            f"Could not find holdings CSV link on {product_url}. "
            "Download manually and place in data/holdings/manual/."
        )

    url = matches[0]
    if url.startswith("/"):
        url = "https://www.globalxetfs.com" + url
    return url