"""
Performance engine.

Reads monthly_returns.xlsx and etf_monthly_performance.xlsx and produces
all metrics needed for PDF pages 2 and 3:

  - Monthly returns table (portfolio vs benchmark)
  - Cumulative YTD returns series (for line chart)
  - Monthly bar chart data
  - Best & worst ETF performers
  - Market exposure breakdown (for donut charts on page 2)

Classification source: src/classification.py (single source of truth).
The `etf_classification_path` argument is kept for backward compatibility
but is IGNORED — pass any path (or None).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from .classification import get_classification_df


def run_performance(
    monthly_returns_path: Path,
    etf_performance_path: Path,
    etf_classification_path: Optional[Path],   # kept for backward compat — ignored
    portfolio_weights_path: Path,
) -> dict:
    """
    Main entry point. Returns a dict of DataFrames / series ready for
    the PDF generator and dashboard.
    """
    monthly   = _load_monthly_returns(monthly_returns_path)
    etf_perf  = _load_etf_performance(etf_performance_path)
    classify  = get_classification_df()                                # ← was pd.read_excel
    weights   = pd.read_excel(portfolio_weights_path).dropna(subset=["ETF Ticker"])

    monthly    = _compute_cumulative(monthly)
    table      = _monthly_table(monthly)
    best_worst = _best_worst(etf_perf)
    market_exp = _market_exposure(weights, classify)

    return {
        "monthly_table":   table,
        "cumulative":      monthly,
        "best_worst":      best_worst,
        "market_exposure": market_exp,
    }


# ── loaders ────────────────────────────────────────────────────────────────

def _load_monthly_returns(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    rename = {}
    for c in df.columns:
        cl = c.lower()
        if "month" in cl:
            rename[c] = "Month"
        elif "portfolio" in cl:
            rename[c] = "Portfolio (%)"
        elif "benchmark" in cl or "acwi" in cl:
            rename[c] = "Benchmark (%)"
    df = df.rename(columns=rename)

    required = ["Month", "Portfolio (%)", "Benchmark (%)"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"monthly_returns.xlsx missing columns: {missing}")

    df = df.dropna(subset=["Month"])
    df["Portfolio (%)"]  = pd.to_numeric(df["Portfolio (%)"],  errors="coerce")
    df["Benchmark (%)"]  = pd.to_numeric(df["Benchmark (%)"],  errors="coerce")
    df = df.dropna(subset=["Portfolio (%)", "Benchmark (%)"])
    df = df.sort_values("Month").reset_index(drop=True)
    return df


def _load_etf_performance(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]

    rename = {}
    for c in df.columns:
        cl = c.lower()
        if "ticker" in cl:
            rename[c] = "Ticker"
        elif "name" in cl:
            rename[c] = "ETF Name"
        elif "return" in cl or "performance" in cl:
            rename[c] = "Monthly Return (%)"
    df = df.rename(columns=rename)
    df["Monthly Return (%)"] = pd.to_numeric(df.get("Monthly Return (%)", pd.Series()), errors="coerce")
    return df


# ── calculations ───────────────────────────────────────────────────────────

def _compute_cumulative(df: pd.DataFrame) -> pd.DataFrame:
    """Add cumulative YTD return columns."""
    df = df.copy()
    df["Cum_Portfolio (%)"] = (
        (1 + df["Portfolio (%)"] / 100).cumprod() - 1
    ) * 100
    df["Cum_Benchmark (%)"] = (
        (1 + df["Benchmark (%)"] / 100).cumprod() - 1
    ) * 100
    return df


def _monthly_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build the display table for PDF page 3."""
    out = df.copy()
    out["Outperformance (%)"] = (out["Portfolio (%)"] - out["Benchmark (%)"]).round(2)
    out["Portfolio (%)"]  = out["Portfolio (%)"].round(2)
    out["Benchmark (%)"]  = out["Benchmark (%)"].round(2)

    def fmt_month(m):
        try:
            return pd.to_datetime(str(m) + "-01").strftime("%B %Y")
        except Exception:
            return str(m)

    out["Month Label"] = out["Month"].apply(fmt_month)

    ytd_port  = out["Cum_Portfolio (%)"].iloc[-1]
    ytd_bench = out["Cum_Benchmark (%)"].iloc[-1]
    ytd_row = pd.DataFrame([{
        "Month":               "YTD",
        "Month Label":         "YTD Cumulative",
        "Portfolio (%)":       round(ytd_port, 2),
        "Benchmark (%)":       round(ytd_bench, 2),
        "Outperformance (%)":  round(ytd_port - ytd_bench, 2),
        "Cum_Portfolio (%)":   round(ytd_port, 2),
        "Cum_Benchmark (%)":   round(ytd_bench, 2),
    }])
    out = pd.concat([out, ytd_row], ignore_index=True)
    return out


def _best_worst(etf_perf: pd.DataFrame, n: int = 3) -> dict:
    """Return top-n gainers and laggards for the month."""
    if "Monthly Return (%)" not in etf_perf.columns:
        return {"gainers": [], "laggards": []}

    valid = etf_perf.dropna(subset=["Monthly Return (%)"])
    sorted_df = valid.sort_values("Monthly Return (%)", ascending=False).reset_index(drop=True)

    def to_list(df):
        return [
            {
                "ticker": str(row.get("Ticker", "")),
                "name":   str(row.get("ETF Name", "")),
                "return": float(row["Monthly Return (%)"]),
            }
            for _, row in df.iterrows()
        ]

    gainers  = to_list(sorted_df.head(n))
    laggards = to_list(sorted_df.tail(n).sort_values("Monthly Return (%)"))
    return {"gainers": gainers, "laggards": laggards}


def _market_exposure(weights: pd.DataFrame, classify: pd.DataFrame) -> dict:
    """
    Compute the two donut charts on PDF page 2:
      by_market: Emerging Markets / Developed Markets / Commodity
      by_type:   Equity ETFs / Commodity ETFs / Cash
    """
    merged = weights.merge(classify, left_on="ETF Ticker", right_on="Ticker", how="left")

    by_market: dict[str, float] = {}
    by_type:   dict[str, float] = {}

    for _, row in merged.iterrows():
        w = float(row.get("Portfolio Weight (%)", 0) or 0)
        market = str(row.get("Market Type", "Unknown")).strip()
        etype  = str(row.get("ETF Type",    "Unknown")).strip()

        etype_label = "Commodity ETFs" if etype.lower() == "commodity" else "Equity ETFs"

        by_market[market]      = by_market.get(market, 0) + w
        by_type[etype_label]   = by_type.get(etype_label, 0) + w

    by_market = {k: round(v, 1) for k, v in sorted(by_market.items(), key=lambda x: -x[1])}
    by_type   = {k: round(v, 1) for k, v in sorted(by_type.items(),   key=lambda x: -x[1])}

    return {"by_market": by_market, "by_type": by_type}
