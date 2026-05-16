"""
iShares holdings fetcher — direct CSV download with retry + delays.
"""
from __future__ import annotations
import logging
import time
from io import StringIO
from typing import Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

ISHARES_URLS = {
    "ARTY": "https://www.ishares.com/us/products/297905/ishares-future-ai-tech-etf/1467271812596.ajax?fileType=csv&fileName=ARTY_holdings&dataType=fund",
    "EEM":  "https://www.ishares.com/us/products/239637/ishares-msci-emerging-markets-etf/1467271812596.ajax?fileType=csv&fileName=EEM_holdings&dataType=fund",
    "IYZ":  "https://www.ishares.com/us/products/239509/ishares-us-telecommunications-etf/1467271812596.ajax?fileType=csv&fileName=IYZ_holdings&dataType=fund",
    "EPOL": "https://www.ishares.com/us/products/239668/ishares-msci-poland-etf/1467271812596.ajax?fileType=csv&fileName=EPOL_holdings&dataType=fund",
    "EWT":  "https://www.ishares.com/us/products/239686/ishares-msci-taiwan-etf/1467271812596.ajax?fileType=csv&fileName=EWT_holdings&dataType=fund",
    "EWZ":  "https://www.ishares.com/us/products/239612/ishares-msci-brazil-etf/1467271812596.ajax?fileType=csv&fileName=EWZ_holdings&dataType=fund",
    "EWA":  "https://www.ishares.com/us/products/239607/ishares-msci-australia-etf/1467271812596.ajax?fileType=csv&fileName=EWA_holdings&dataType=fund",
    "MCHI": "https://www.ishares.com/us/products/239619/ishares-msci-china-etf/1467271812596.ajax?fileType=csv&fileName=MCHI_holdings&dataType=fund",
    "IAU":  None,  # Grantor trust — physical gold, synthesised below
}

IAU_SYNTHETIC = pd.DataFrame([{
    "Ticker":        "GOLD",
    "Security Name": "Physical Gold",
    "Weight (%)":    100.0,
    "Sector":        "Commodities",
    "Country":       "United States",
    "Asset Class":   "Commodity",
}])

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":         "https://www.ishares.com/us/products/etf-investments",
    "Connection":      "keep-alive",
}

# Delay between consecutive iShares requests (seconds)
# Spread the load — iShares rate-limits burst traffic
INTER_REQUEST_DELAY = 3.0

# Track last request time across calls
_last_request_time: float = 0.0


def _get_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,          # waits 2s, 4s, 8s between retries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://",  adapter)
    return session


def fetch_ishares(ticker: str, product_url: Optional[str] = None) -> pd.DataFrame:
    global _last_request_time

    if ticker == "IAU":
        return IAU_SYNTHETIC.copy()

    url = ISHARES_URLS.get(ticker)
    if url is None:
        raise ValueError(f"No iShares URL configured for {ticker}")

    # Polite delay — don't hammer iShares
    elapsed = time.time() - _last_request_time
    if elapsed < INTER_REQUEST_DELAY:
        time.sleep(INTER_REQUEST_DELAY - elapsed)

    session = _get_session()
    response = session.get(url, headers=HEADERS, timeout=45)
    _last_request_time = time.time()
    response.raise_for_status()

    return _parse_ishares_csv(response.text, ticker)


def _parse_ishares_csv(text: str, ticker: str) -> pd.DataFrame:
    lines = text.splitlines()
    header_idx = None

    for i, line in enumerate(lines):
        cols = [c.strip().strip('"').lower() for c in line.split(",")]
        has_weight = "weight (%)" in cols
        has_id = any(c in cols for c in ["ticker", "name", "isin"])
        if has_weight and has_id and len(cols) >= 3:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"Could not find header row in iShares CSV for {ticker}.")

    df = pd.read_csv(StringIO("\n".join(lines[header_idx:])))
    df.columns = [c.strip() for c in df.columns]

    if "Ticker" in df.columns:
        df = df[df["Ticker"].notna() & (df["Ticker"].astype(str).str.strip() != "")]
    if "Name" in df.columns and "Security Name" not in df.columns:
        df = df.rename(columns={"Name": "Security Name"})
    if "Location" in df.columns and "Country" not in df.columns:
        df = df.rename(columns={"Location": "Country"})
    if "Ticker" not in df.columns:
        df["Ticker"] = df.get("ISIN", df.get("Security Name", "UNKNOWN"))

    return df