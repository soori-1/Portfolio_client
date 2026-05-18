"""
ETF Classification — Single Source of Truth
============================================

Replaces data/config/etf_classification.xlsx.

Every ETF in the portfolio has:
  - market_type: Emerging Markets | Developed Markets | Commodity
  - etf_type:    Equity | Commodity

Adding a new ETF to portfolio_weights.xlsx? Add a row here too.
If you forget, classify_etf() returns sensible defaults from the
issuer ticker sets in src/fetchers/__init__.py.

This module has ZERO dependencies — safe to import from anywhere.
"""
from __future__ import annotations

import pandas as pd


# ── Master classification table ─────────────────────────────────────────────
# Every ticker in the current Momentum Global ETF Portfolio.
# Add new rows when adding ETFs.
CLASSIFICATION: dict[str, dict[str, str]] = {
    # Emerging Markets — Equity
    "EEM":  {"market_type": "Emerging Markets",  "etf_type": "Equity"},
    "MCHI": {"market_type": "Emerging Markets",  "etf_type": "Equity"},
    "EWT":  {"market_type": "Emerging Markets",  "etf_type": "Equity"},
    "EWZ":  {"market_type": "Emerging Markets",  "etf_type": "Equity"},
    "EPOL": {"market_type": "Emerging Markets",  "etf_type": "Equity"},

    # Developed Markets — Equity
    "VT":   {"market_type": "Developed Markets", "etf_type": "Equity"},
    "ARTY": {"market_type": "Developed Markets", "etf_type": "Equity"},
    "IYZ":  {"market_type": "Developed Markets", "etf_type": "Equity"},
    "EWA":  {"market_type": "Developed Markets", "etf_type": "Equity"},
    "DTCR": {"market_type": "Developed Markets", "etf_type": "Equity"},
    "LIT":  {"market_type": "Developed Markets", "etf_type": "Equity"},
    "HYDR": {"market_type": "Developed Markets", "etf_type": "Equity"},
    "TAN":  {"market_type": "Developed Markets", "etf_type": "Equity"},

    # Commodities — physical / futures
    "IAU":  {"market_type": "Commodity", "etf_type": "Commodity"},
    "SLV":  {"market_type": "Commodity", "etf_type": "Commodity"},
    "CPER": {"market_type": "Commodity", "etf_type": "Commodity"},
}


# ── Fallback ticker sets (mirror src/fetchers/__init__.py) ──────────────────
# Used only when an unknown ticker shows up — keeps the dashboard from
# breaking. If you see "Unknown" in the live dashboard, add a proper
# row to CLASSIFICATION above.
_COMMODITY_FALLBACK = {
    "IAU","SLV","GLD","PPLT","PALL","SGOL","SIVR","BAR",
    "CPER","DBB","DBC","DBO","DBP","DBS",
}

_EMERGING_FALLBACK = {
    "EEM","MCHI","EWT","EWZ","EPOL","INDA","ASHR","VWO","IEMG",
    "EWY","EZA","TUR","EWW","EIDO","EPHE","THD","EPU","ARGT",
}


def classify_etf(ticker: str) -> dict[str, str]:
    """
    Return {market_type, etf_type} for a ticker.

    1. Look up in CLASSIFICATION (authoritative).
    2. Fallback to ticker-set heuristics.
    3. Last resort: Developed Markets / Equity (safe default for unknown ETFs).
    """
    t = (ticker or "").upper().strip()
    if t in CLASSIFICATION:
        return CLASSIFICATION[t]
    if t in _COMMODITY_FALLBACK:
        return {"market_type": "Commodity", "etf_type": "Commodity"}
    if t in _EMERGING_FALLBACK:
        return {"market_type": "Emerging Markets", "etf_type": "Equity"}
    return {"market_type": "Developed Markets", "etf_type": "Equity"}


def get_classification_df() -> pd.DataFrame:
    """
    Return CLASSIFICATION as a DataFrame matching the legacy xlsx schema:
      columns: Ticker, Market Type, ETF Type

    Drop-in replacement for `pd.read_excel(etf_classification_path)`.
    """
    rows = [
        {"Ticker": tk, "Market Type": v["market_type"], "ETF Type": v["etf_type"]}
        for tk, v in CLASSIFICATION.items()
    ]
    return pd.DataFrame(rows)
