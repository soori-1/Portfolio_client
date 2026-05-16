"""
Look-through analytics engine.

Takes holdings for all ETFs + portfolio weights and produces:
  - Stock-level aggregated exposure (single row per security)
  - Sector allocation (GICS)
  - Country allocation
  - Concentration metrics
  - Per-ETF summary
  - Data quality report
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from .normalize import normalize_sector, normalize_country

log = logging.getLogger(__name__)

# IAU is excluded from look-through — treated as a pure Commodities allocation
EXCLUDE_FROM_LOOKTHROUGH = {"IAU"}


def run_lookthrough(
    holdings: dict[str, pd.DataFrame],
    portfolio_weights: pd.DataFrame,
    ticker_aliases: Optional[pd.DataFrame] = None,
    sector_overrides: Optional[pd.DataFrame] = None,
    country_overrides: Optional[pd.DataFrame] = None,
) -> dict[str, pd.DataFrame]:
    """
    Main entry point. Returns a dict of DataFrames keyed by sheet name,
    ready to be written to lookthrough.xlsx.
    """
    weights = _build_weight_map(portfolio_weights)

    # Build alias map: source_ticker -> canonical_ticker
    alias_map = _build_alias_map(ticker_aliases)

    # Build override maps
    sector_override_map = _build_override_map(sector_overrides, "Ticker", "Override Sector")
    country_override_map = _build_override_map(country_overrides, "Ticker", "Override Country")

    # Expand each ETF's holdings to portfolio-level weights
    rows = []
    excluded_etfs = {}

    for etf_ticker, df in holdings.items():
        if etf_ticker in EXCLUDE_FROM_LOOKTHROUGH:
            excluded_etfs[etf_ticker] = df
            log.info("Excluding %s from look-through (commodity ETF)", etf_ticker)
            continue

        etf_weight = weights.get(etf_ticker, 0.0) / 100.0  # fraction
        if etf_weight == 0:
            log.warning("ETF %s has no portfolio weight — skipping", etf_ticker)
            continue

        for _, holding in df.iterrows():
            holding_weight_pct = pd.to_numeric(holding.get("Weight (%)"), errors="coerce")
            if pd.isna(holding_weight_pct) or holding_weight_pct <= 0:
                continue

            raw_ticker = str(holding.get("Ticker", "")).strip()
            canonical_ticker = alias_map.get(raw_ticker, raw_ticker)

            security_name = str(holding.get("Security Name", "")).strip()
            raw_sector = holding.get("Sector")
            raw_country = holding.get("Country")

            # Apply overrides first, then normalize
            if canonical_ticker in sector_override_map:
                sector = sector_override_map[canonical_ticker]
            else:
                sector = normalize_sector(raw_sector, security_name)

            if canonical_ticker in country_override_map:
                country = country_override_map[canonical_ticker]
            else:
                country = normalize_country(raw_country)

            # Portfolio-level weight = ETF weight in portfolio × holding weight in ETF
            portfolio_weight = etf_weight * (holding_weight_pct / 100.0) * 100.0

            rows.append({
                "Canonical Ticker":  canonical_ticker,
                "Original Ticker":   raw_ticker,
                "Security Name":     security_name,
                "Sector":            sector,
                "Country":           country,
                "ETF":               etf_ticker,
                "Weight in ETF (%)": round(holding_weight_pct, 4),
                "Portfolio Weight (%)": round(portfolio_weight, 4),
            })

    if not rows:
        raise ValueError("No holdings rows produced — check ETF holdings and portfolio weights.")

    raw = pd.DataFrame(rows)

    # Aggregate: one row per canonical ticker
    stock_level = _aggregate_stocks(raw)

    # Sector and country rollups
    sector_exp = _rollup(stock_level, "Sector")
    country_exp = _rollup(stock_level, "Country")

    # Concentration
    concentration = _concentration_metrics(stock_level, weights, excluded_etfs)

    # Per-ETF summary
    etf_summary = _etf_summary(raw, weights, holdings)

    # Data quality
    quality = _data_quality(raw, stock_level)

    return {
        "Stock Look-Through":   stock_level,
        "Sector Exposure":      sector_exp,
        "Country Exposure":     country_exp,
        "Concentration":        concentration,
        "ETF Summary":          etf_summary,
        "Data Quality":         quality,
    }


def _build_weight_map(portfolio_weights: pd.DataFrame) -> dict[str, float]:
    """Return {ticker: weight%} from portfolio_weights DataFrame."""
    w = {}
    for _, row in portfolio_weights.iterrows():
        ticker = str(row.get("ETF Ticker", "")).strip()
        weight = pd.to_numeric(row.get("Portfolio Weight (%)"), errors="coerce")
        if ticker and not pd.isna(weight):
            w[ticker] = float(weight)
    return w


def _build_alias_map(aliases: Optional[pd.DataFrame]) -> dict[str, str]:
    if aliases is None or aliases.empty:
        return {}
    m = {}
    for _, row in aliases.iterrows():
        src = str(row.get("Source Ticker", "")).strip()
        canon = str(row.get("Canonical Ticker", "")).strip()
        if src and canon:
            m[src] = canon
    return m


def _build_override_map(df: Optional[pd.DataFrame], key_col: str, val_col: str) -> dict[str, str]:
    if df is None or df.empty:
        return {}
    m = {}
    for _, row in df.iterrows():
        k = str(row.get(key_col, "")).strip()
        v = str(row.get(val_col, "")).strip()
        if k and v and v not in ("nan", ""):
            m[k] = v
    return m


def _aggregate_stocks(raw: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse to one row per canonical ticker.
    Aggregated portfolio weight = sum across all ETFs.
    Contributing ETFs = comma-separated list.
    Sector/Country = mode (most common value across ETFs).
    """
    agg = (
        raw.groupby("Canonical Ticker")
        .agg(
            Security_Name=("Security Name", "first"),
            Sector=("Sector", lambda x: x.mode()[0] if not x.mode().empty else "Unclassified"),
            Country=("Country", lambda x: x.mode()[0] if not x.mode().empty else "Unknown"),
            Portfolio_Weight=("Portfolio Weight (%)", "sum"),
            Contributing_ETFs=("ETF", lambda x: ", ".join(sorted(x.unique()))),
            ETF_Count=("ETF", "nunique"),
        )
        .reset_index()
    )

    agg.columns = [
        "Ticker", "Security Name", "Sector", "Country",
        "Portfolio Weight (%)", "Contributing ETFs", "ETF Count"
    ]
    agg["Portfolio Weight (%)"] = agg["Portfolio Weight (%)"].round(4)
    agg = agg.sort_values("Portfolio Weight (%)", ascending=False).reset_index(drop=True)
    return agg


def _rollup(stock_level: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Sum portfolio weights by sector or country."""
    rollup = (
        stock_level.groupby(group_col)["Portfolio Weight (%)"]
        .sum()
        .reset_index()
        .sort_values("Portfolio Weight (%)", ascending=False)
        .reset_index(drop=True)
    )
    rollup["Portfolio Weight (%)"] = rollup["Portfolio Weight (%)"].round(2)
    total = rollup["Portfolio Weight (%)"].sum()
    rollup["% of Classified"] = (rollup["Portfolio Weight (%)"] / total * 100).round(1)
    return rollup


def _concentration_metrics(
    stock_level: pd.DataFrame,
    weights: dict[str, float],
    excluded_etfs: dict,
) -> pd.DataFrame:
    """Top 10 holdings, HHI, max single-stock weight."""
    top10 = stock_level.head(10)[["Ticker", "Security Name", "Sector", "Country", "Portfolio Weight (%)"]].copy()
    top10_weight = top10["Portfolio Weight (%)"].sum()

    # HHI on look-through stocks (excluding commodity ETFs)
    hhi = (stock_level["Portfolio Weight (%)"] ** 2).sum()

    max_stock = stock_level.iloc[0] if len(stock_level) > 0 else None

    summary_rows = [
        ("Total securities (look-through)",  len(stock_level)),
        ("Top 10 cumulative weight (%)",      round(top10_weight, 2)),
        ("Max single-stock weight (%)",       round(stock_level["Portfolio Weight (%)"].max(), 2) if len(stock_level) else 0),
        ("Max single-stock name",             max_stock["Security Name"] if max_stock is not None else ""),
        ("HHI (stock level)",                 round(float(hhi), 2)),
        ("Excluded ETFs (commodity)",         ", ".join(excluded_etfs.keys()) if excluded_etfs else "None"),
    ]

    summary = pd.DataFrame(summary_rows, columns=["Metric", "Value"])

    # Append top 10 table below
    top10.insert(0, "Rank", range(1, len(top10) + 1))
    return summary, top10


def _etf_summary(
    raw: pd.DataFrame,
    weights: dict[str, float],
    holdings: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    rows = []
    for etf, df in holdings.items():
        etf_weight = weights.get(etf, 0.0)
        n_holdings = len(df)
        top5 = df.nlargest(5, "Weight (%)")[["Ticker", "Security Name", "Weight (%)"]].copy()
        top5_str = "; ".join(
            f"{r['Ticker']} {r['Weight (%)']:.1f}%" for _, r in top5.iterrows()
        )
        rows.append({
            "ETF Ticker":          etf,
            "Portfolio Weight (%)": etf_weight,
            "Holdings Count":      n_holdings,
            "Top 5 Holdings":      top5_str,
        })
    df_out = pd.DataFrame(rows).sort_values("Portfolio Weight (%)", ascending=False).reset_index(drop=True)
    return df_out


def _data_quality(raw: pd.DataFrame, stock_level: pd.DataFrame) -> pd.DataFrame:
    issues = []

    # Unclassified sectors
    unclassified = stock_level[stock_level["Sector"] == "Unclassified"]
    for _, row in unclassified.iterrows():
        issues.append({
            "Issue": "Unclassified Sector",
            "Ticker": row["Ticker"],
            "Security Name": row["Security Name"],
            "Detail": f"Portfolio weight: {row['Portfolio Weight (%)']:.3f}%",
        })

    # Unknown countries
    unknown_country = stock_level[stock_level["Country"] == "Unknown"]
    for _, row in unknown_country.iterrows():
        issues.append({
            "Issue": "Unknown Country",
            "Ticker": row["Ticker"],
            "Security Name": row["Security Name"],
            "Detail": f"Portfolio weight: {row['Portfolio Weight (%)']:.3f}%",
        })

    if not issues:
        return pd.DataFrame([{"Issue": "No data quality issues found", "Ticker": "", "Security Name": "", "Detail": ""}])

    return pd.DataFrame(issues).sort_values("Issue").reset_index(drop=True)
