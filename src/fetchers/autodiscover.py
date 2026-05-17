"""
Auto-discovery fetcher.

Given only a ticker symbol, this module:
1. Looks up the ETF issuer via yfinance metadata
2. Routes to the correct fetcher (iShares, GlobalX, Invesco, Vanguard)
3. Falls back to a generic CSV scraper if the issuer is unknown
4. As a last resort, builds a synthetic single-holding from yfinance data

This means adding a new ETF to portfolio_weights.xlsx is all that's needed.
No manual URL configuration required.
"""
from __future__ import annotations

import logging
import re
import time
from io import StringIO
from typing import Optional

import pandas as pd
import requests

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# Known issuer patterns — matched against ETF name / fund family from yfinance
ISSUER_PATTERNS = {
    "ishares":   ["ishares", "blackrock"],
    "globalx":   ["global x", "globalx", "mirae"],
    "invesco":   ["invesco", "powershares"],
    "vanguard":  ["vanguard"],
    "spdr":      ["spdr", "state street", "ssga"],
    "wisdomtree":["wisdomtree"],
    "vaneck":    ["vaneck", "van eck"],
}

# Known direct CSV URL patterns by issuer
ISSUER_CSV_BUILDERS = {
    "ishares": lambda ticker: (
        f"https://www.ishares.com/us/products/"
        f"{_get_ishares_product_id(ticker)}/"
        f"{ticker.lower()}-etf/1467271812596.ajax"
        f"?fileType=csv&fileName={ticker}_holdings&dataType=fund"
    ),
    "globalx": lambda ticker: (
        f"https://www.globalxetfs.com/funds/{ticker.lower()}/"
    ),
    "invesco": lambda ticker: (
        f"https://www.invesco.com/us/financial-products/etfs/holdings/"
        f"main/holdings/0?audienceType=Investor&action=download&ticker={ticker}"
    ),
}

# iShares product ID cache — populated by lookup
_ISHARES_IDS: dict[str, str] = {
    "EEM": "239637", "ARTY": "297905", "IYZ": "239509",
    "EPOL": "239668", "EWT": "239686", "EWZ": "239612",
    "EWA": "239607", "MCHI": "239619", "IAU": "239561",
    "SLV": "239855",
}


def _get_ishares_product_id(ticker: str) -> str:
    if ticker in _ISHARES_IDS:
        return _ISHARES_IDS[ticker]
    # Try to find via iShares search API
    try:
        url = f"https://www.ishares.com/us/products/etf-investments#/?productView=etf&keywords={ticker}"
        r = requests.get(url, headers=HEADERS, timeout=15)
        match = re.search(r'/us/products/(\d+)/', r.text)
        if match:
            pid = match.group(1)
            _ISHARES_IDS[ticker] = pid
            return pid
    except Exception:
        pass
    return ticker  # fallback — URL will 404, triggering manual fallback


def autodiscover_and_fetch(ticker: str) -> pd.DataFrame:
    """
    Main entry point. Given a ticker, auto-discovers issuer and fetches holdings.
    """
    log.info("Auto-discovering issuer for %s...", ticker)

    # Step 1: Get ETF metadata from yfinance
    meta = _get_etf_meta(ticker)
    issuer = _detect_issuer(meta)
    log.info("%s → detected issuer: %s", ticker, issuer or "unknown")

    # Step 2: Try issuer-specific fetcher
    if issuer == "ishares":
        from .ishares import fetch_ishares
        try:
            return fetch_ishares(ticker)
        except Exception as e:
            log.warning("iShares fetcher failed for %s: %s", ticker, e)

    elif issuer == "globalx":
        from .globalx import fetch_globalx
        try:
            return fetch_globalx(ticker)
        except Exception as e:
            log.warning("GlobalX fetcher failed for %s: %s", ticker, e)

    elif issuer == "invesco":
        from .invesco import fetch_invesco
        try:
            return fetch_invesco(ticker)
        except Exception as e:
            log.warning("Invesco fetcher failed for %s: %s", ticker, e)

    elif issuer == "vanguard":
        from .vanguard import fetch_vanguard
        try:
            return fetch_vanguard(ticker)
        except Exception as e:
            log.warning("Vanguard fetcher failed for %s: %s", ticker, e)

    # Step 3: Generic scraper — try ETF.com or similar
    try:
        df = _generic_holdings_scrape(ticker)
        if df is not None and len(df) > 0:
            return df
    except Exception as e:
        log.warning("Generic scrape failed for %s: %s", ticker, e)

    # Step 4: Synthetic fallback — build from yfinance top holdings
    log.warning("All fetchers failed for %s — building synthetic from yfinance", ticker)
    return _synthetic_from_yfinance(ticker, meta)


def _get_etf_meta(ticker: str) -> dict:
    """Get ETF metadata from yfinance."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        return {
            "name":        info.get("longName", ""),
            "fund_family": info.get("fundFamily", ""),
            "category":    info.get("category", ""),
            "sector":      info.get("sector", ""),
            "holdings":    info.get("holdings", []),
            "top_holdings": info.get("topHoldings", []),
        }
    except Exception as e:
        log.warning("yfinance metadata fetch failed for %s: %s", ticker, e)
        return {}


def _detect_issuer(meta: dict) -> Optional[str]:
    """Detect ETF issuer from metadata."""
    text = " ".join([
        meta.get("name", ""),
        meta.get("fund_family", ""),
    ]).lower()

    for issuer, patterns in ISSUER_PATTERNS.items():
        if any(p in text for p in patterns):
            return issuer
    return None


def _generic_holdings_scrape(ticker: str) -> Optional[pd.DataFrame]:
    """
    Try ETF.com holdings page — works for many smaller ETFs.
    ETF.com has a standardised holdings table for most US-listed ETFs.
    """
    url = f"https://www.etf.com/{ticker}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None

        # Parse holdings table from HTML
        tables = pd.read_html(StringIO(r.text))
        for t in tables:
            cols = [c.lower() for c in t.columns]
            if any("weight" in c or "%" in c for c in cols):
                # Likely a holdings table
                t.columns = [c.strip() for c in t.columns]
                # Normalise
                for c in t.columns:
                    cl = c.lower()
                    if "name" in cl and "Security Name" not in t.columns:
                        t = t.rename(columns={c: "Security Name"})
                    elif ("weight" in cl or "%" in cl) and "Weight (%)" not in t.columns:
                        t = t.rename(columns={c: "Weight (%)"})
                    elif "ticker" in cl or "symbol" in cl and "Ticker" not in t.columns:
                        t = t.rename(columns={c: "Ticker"})
                if "Security Name" in t.columns and "Weight (%)" in t.columns:
                    if "Ticker" not in t.columns:
                        t["Ticker"] = t["Security Name"].str[:8]
                    return t
        return None
    except Exception as e:
        log.debug("ETF.com scrape failed: %s", e)
        return None


def _synthetic_from_yfinance(ticker: str, meta: dict) -> pd.DataFrame:
    """
    Build a synthetic holdings DataFrame from yfinance top holdings data.
    This is the last resort — gives approximate sector/country exposure
    based on whatever yfinance returns for this ETF.
    """
    rows = []

    # Try yfinance holdings
    holdings = meta.get("holdings", []) or meta.get("top_holdings", [])
    if holdings:
        for h in holdings[:20]:
            rows.append({
                "Ticker":        h.get("symbol", "UNKNOWN"),
                "Security Name": h.get("holdingName", h.get("symbol", "")),
                "Weight (%)":    float(h.get("holdingPercent", 0)) * 100,
                "Sector":        h.get("sector", ""),
                "Country":       "",
                "Asset Class":   "Equity",
            })

    if not rows:
        # Absolute fallback — single synthetic row
        name = meta.get("name", f"{ticker} ETF")
        rows.append({
            "Ticker":        ticker,
            "Security Name": name,
            "Weight (%)":    100.0,
            "Sector":        _guess_sector(meta),
            "Country":       _guess_country(meta),
            "Asset Class":   "Equity",
        })

    return pd.DataFrame(rows)


def _guess_sector(meta: dict) -> str:
    """Guess GICS sector from ETF name/category."""
    text = " ".join([
        meta.get("name", ""),
        meta.get("category", ""),
        meta.get("sector", ""),
    ]).lower()

    sector_keywords = {
        "Information Technology": ["tech", "semiconductor", "ai", "software", "digital", "data center"],
        "Energy":                 ["energy", "solar", "wind", "hydrogen", "oil", "gas", "clean energy"],
        "Materials":              ["materials", "lithium", "copper", "silver", "gold", "mining", "metals"],
        "Financials":             ["financial", "bank", "insurance", "fintech"],
        "Health Care":            ["health", "biotech", "pharma", "medical"],
        "Industrials":            ["industrial", "aerospace", "defense", "infrastructure"],
        "Real Estate":            ["real estate", "reit", "property"],
        "Commodities":            ["commodity", "gold", "silver", "copper", "precious"],
    }

    for sector, keywords in sector_keywords.items():
        if any(kw in text for kw in keywords):
            return sector
    return "Unclassified"


def _guess_country(meta: dict) -> str:
    """Guess primary country from ETF name."""
    text = meta.get("name", "").lower()
    country_map = {
        "United States": ["u.s.", "us ", "united states", "american", "s&p", "nasdaq", "dow"],
        "China":         ["china", "chinese", "msci china"],
        "Taiwan":        ["taiwan"],
        "Brazil":        ["brazil", "brazilian"],
        "Poland":        ["poland", "polish"],
        "Australia":     ["australia", "australian"],
        "India":         ["india", "indian"],
        "Japan":         ["japan", "japanese"],
    }
    for country, keywords in country_map.items():
        if any(kw in text for kw in keywords):
            return country
    return "Global"

def _commodity_synthetic(ticker: str) -> pd.DataFrame:
    """Synthetic single-row holding for commodity grantor trusts."""
    names = {
        "IAU": "Physical Gold",
        "SLV": "Physical Silver", 
        "GLD": "Physical Gold",
        "CPER": "Copper Futures",
        "PPLT": "Physical Platinum",
        "PALL": "Physical Palladium",
    }
    return pd.DataFrame([{
        "Ticker":        ticker,
        "Security Name": names.get(ticker, f"{ticker} Holdings"),
        "Weight (%)":    100.0,
        "Sector":        "Commodities",
        "Country":       "United States",
        "Asset Class":   "Commodity",
    }])
