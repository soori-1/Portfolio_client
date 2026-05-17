"""
Holdings fetcher router.

Works entirely from portfolio_weights.xlsx — no etf_sources.xlsx needed.

Adding a ticker to portfolio_weights.xlsx is sufficient.
The router auto-detects the issuer and fetches holdings automatically.

Known issuers (fast path, no network lookup):
  iShares tickers in ISHARES_TICKERS → direct CSV download
  GlobalX tickers in GLOBALX_TICKERS → direct CSV download
  Vanguard tickers in VANGUARD_TICKERS → manual CSV (Vanguard blocks automation)
  Commodity trusts in COMMODITY_TICKERS → synthetic holding (no real holdings)

Unknown tickers → autodiscover (yfinance lookup → ETF.com scraper → synthetic)
"""
from __future__ import annotations

import logging
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from .autodiscover import autodiscover_and_fetch

# Lazy imports — only loaded when actually needed
def _lazy_ishares(): from .ishares import fetch_ishares; return fetch_ishares
def _lazy_vanguard(): from .vanguard import fetch_vanguard; return fetch_vanguard
def _lazy_globalx(): from .globalx import fetch_globalx; return fetch_globalx
def _lazy_invesco():
    try:
        from .invesco import fetch_invesco
        return fetch_invesco
    except ImportError:
        return None

log = logging.getLogger(__name__)

# ── Known ticker → issuer mapping (no network lookup needed) ─────────────────
ISHARES_TICKERS = {
    "EEM","ARTY","IYZ","EPOL","EWT","EWZ","EWA","MCHI","IAU","SLV",
    "AGG","IVV","IJH","IJR","IWM","IWF","IWD","IEF","TLT","LQD",
    "HYG","EMB","MBB","IEFA","IEMG","ACWI","IDV","IXUS",
}

GLOBALX_TICKERS = {
    "DTCR","LIT","HYDR","COPX","AIQ","SNSR","FINX","HERO","CLOU",
    "BOTZ","DRIV","BKCH","GNOM","CTEC","MLPA","PFFD",
}

INVESCO_TICKERS = {
    "TAN","QQQ","RSP","SQQQ","TQQQ","PGX","PDBC","PBND",
    "PHO","PBW","PSCI","PSCT","PSCE","PSCC","PSCF",
}

VANGUARD_TICKERS = {
    "VT","VTI","VOO","VEA","VWO","BND","BNDX","VIG","VYM",
    "VGT","VHT","VFH","VCR","VDC","VDE","VIS","VMO","VNQ",
}

# Commodity grantor trusts — physical assets, no stock holdings
COMMODITY_TICKERS = {
    "IAU","SLV","GLD","PPLT","PALL","SGOL","SIVR","BAR",
    "CPER","DBB","DBC","DBO","DBP","DBS",
}

def get_fetcher(issuer):
    """Get fetcher function lazily — survives missing modules."""
    loaders = {
        "ishares":  _lazy_ishares,
        "vanguard": _lazy_vanguard,
        "globalx":  _lazy_globalx,
        "invesco":  _lazy_invesco,
    }
    loader = loaders.get(issuer)
    if loader:
        try:
            return loader()
        except ImportError:
            return None
    return None


def _detect_issuer(ticker: str) -> str:
    """Detect issuer from ticker alone — no network call."""
    t = ticker.upper()
    if t in ISHARES_TICKERS:   return "ishares"
    if t in GLOBALX_TICKERS:   return "globalx"
    if t in INVESCO_TICKERS:   return "invesco"
    if t in VANGUARD_TICKERS:  return "vanguard"
    if t in COMMODITY_TICKERS: return "commodity"
    return "auto"


def fetch_all_holdings(
    config_path: Path,           # points to portfolio_weights.xlsx OR etf_sources.xlsx
    cache_root: Path,
    manual_root: Path,
    as_of: Optional[date] = None,
    force_refresh: bool = False,
) -> dict[str, pd.DataFrame]:

    as_of = as_of or date.today()
    cache_dir = _find_or_create_cache_dir(cache_root, as_of, force_refresh)

    # Load ticker list from portfolio_weights.xlsx (primary) or etf_sources (legacy)
    tickers = _load_tickers(config_path)

    results: dict[str, pd.DataFrame] = {}
    errors:  dict[str, str] = {}

    for ticker in tickers:
        try:
            df = _fetch_one(ticker, cache_dir, manual_root)
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


def _load_tickers(config_path: Path) -> list[str]:
    """Load ticker list — works with portfolio_weights.xlsx or etf_sources.xlsx."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    df = pd.read_excel(config_path)
    df.columns = [c.strip() for c in df.columns]

    # portfolio_weights.xlsx has "ETF Ticker" column
    if "ETF Ticker" in df.columns:
        df = df.dropna(subset=["ETF Ticker"])
        tickers = df["ETF Ticker"].astype(str).str.strip().tolist()
        return [t for t in tickers if t and t.upper() not in ("TOTAL","NAN","")]

    # etf_sources.xlsx has "Ticker" column (legacy support)
    if "Ticker" in df.columns:
        return df["Ticker"].astype(str).str.strip().dropna().tolist()

    raise ValueError(f"Cannot find ticker column in {config_path}")


def _fetch_one(ticker: str, cache_dir: Path, manual_root: Path) -> pd.DataFrame:
    """Fetch holdings for a single ETF."""
    cached = cache_dir / f"{ticker}.csv"
    if cached.exists():
        try:
            df = _load_standardized(cached)
            print(f"       (cached, {len(df)} holdings)")
            return df
        except Exception as e:
            print(f"       cached file corrupt ({e}), refetching")
            try:
                cached.unlink()
            except Exception:
                pass

    manual = manual_root / f"{ticker}.csv"
    issuer = _detect_issuer(ticker)

    print(f"       fetching [{issuer}]...")

    # Manual-only ETFs
    if issuer == "vanguard":
        if manual.exists():
            df = _load_standardized(manual)
            df.to_csv(cached, index=False)
            return df
        # Try fetcher anyway — sometimes works
        try:
            df = fetch_vanguard(ticker=ticker)
            df = _standardize(df)
            df.to_csv(cached, index=False)
            return df
        except Exception:
            raise RuntimeError(
                f"{ticker} (Vanguard): place manual CSV at {manual}"
            )

    # Commodity trusts — synthetic
    if issuer == "commodity":
        from .autodiscover import _commodity_synthetic
        df = _commodity_synthetic(ticker)
        df = _standardize(df)
        df.to_csv(cached, index=False)
        return df

    # Manual CSV takes precedence — most reliable, especially when issuers block
    if manual.exists():
        print(f"       using manual CSV")
        df = _load_standardized(manual)
        df.to_csv(cached, index=False)
        return df

    # Known issuers — direct fetcher (may fail if issuer blocks)
    fetcher = get_fetcher(issuer)
    if fetcher is not None:
        try:
            df = fetcher(ticker=ticker)
            df = _standardize(df)
            df.to_csv(cached, index=False)
            return df
        except Exception as e:
            print(f"       fetch error: {e}")
            print(f"       trying auto-discovery...")

    # Auto-discovery for unknown tickers
    try:
        df = autodiscover_and_fetch(ticker)
        df = _standardize(df)
        df.to_csv(cached, index=False)
        return df
    except Exception as e:
        if manual.exists():
            df = _load_standardized(manual)
            df.to_csv(cached, index=False)
            return df
        # Last resort — build minimal synthetic so pipeline doesn't crash
        print(f"       building minimal synthetic for {ticker}")
        df = pd.DataFrame([{
            "Ticker":        ticker,
            "Security Name": f"{ticker} (holdings unavailable)",
            "Weight (%)":    100.0,
            "Sector":        "Unclassified",
            "Country":       "Global",
            "Asset Class":   "Equity",
        }])
        df.to_csv(cached, index=False)
        return df


def _find_or_create_cache_dir(cache_root: Path, as_of: date, force_refresh: bool) -> Path:
    today_dir = cache_root / as_of.isoformat()

    if force_refresh:
        if today_dir.exists():
            shutil.rmtree(today_dir)
        try:
            today_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Read-only filesystem (Render) — use /tmp
            today_dir = Path("/tmp") / "rh_cache" / as_of.isoformat()
            today_dir.mkdir(parents=True, exist_ok=True)
        return today_dir

    if today_dir.exists() and any(today_dir.glob("*.csv")):
        return today_dir

    # Look for ANY cached holdings in repo — prefer most recent
    if cache_root.exists():
        candidates = sorted(
            [d for d in cache_root.iterdir()
             if d.is_dir() and any(d.glob("*.csv"))],
            reverse=True
        )
        if candidates:
            best = candidates[0]
            print(f"  (using cached holdings from {best.name})")
            try:
                today_dir.mkdir(parents=True, exist_ok=True)
                for f in best.glob("*.csv"):
                    dst = today_dir / f.name
                    if not dst.exists():
                        shutil.copy2(f, dst)
                return today_dir
            except Exception:
                # Read-only — just return the existing cache dir directly
                return best

    try:
        today_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        today_dir = Path("/tmp") / "rh_cache" / as_of.isoformat()
        today_dir.mkdir(parents=True, exist_ok=True)
    return today_dir


REQUIRED_COLS = ["Ticker", "Security Name", "Weight (%)"]
OPTIONAL_COLS = ["Sector", "Country", "Asset Class"]


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
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


def _load_standardized(path: Path) -> pd.DataFrame:
    """
    Load a manual CSV, handling iShares/GlobalX/Invesco multi-line metadata headers.
    Scans for the actual data header row before parsing.
    """
    # Read raw lines to find the actual header
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    header_idx = 0
    for i, line in enumerate(lines):
        cols = [c.strip().strip('"').lower() for c in line.split(',')]
        # Header row has both a name-like and a weight-like column
        has_name   = any('name' in c or 'security' in c or 'holding' in c for c in cols)
        has_weight = any('weight' in c for c in cols)
        has_ticker = any('ticker' in c or 'symbol' in c for c in cols)
        if (has_name or has_ticker) and has_weight and len(cols) >= 3:
            header_idx = i
            break

    # Re-read from the header row
    df = pd.read_csv(path, skiprows=header_idx, on_bad_lines='skip')
    df.columns = [c.strip() for c in df.columns]

    # Normalise common column variations
    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if 'security name' in cl or 'name' == cl or 'holding name' in cl:
            rename_map[c] = 'Security Name'
        elif 'weight' in cl and '%' in cl:
            rename_map[c] = 'Weight (%)'
        elif cl == 'weight':
            rename_map[c] = 'Weight (%)'
        elif cl in ('ticker', 'symbol', 'ticker symbol'):
            rename_map[c] = 'Ticker'
        elif cl == 'sector':
            rename_map[c] = 'Sector'
        elif cl in ('country', 'location', 'market'):
            rename_map[c] = 'Country'
        elif 'asset' in cl and 'class' in cl:
            rename_map[c] = 'Asset Class'
    df = df.rename(columns=rename_map)

    # Ticker fallback — synthesize from name if missing
    if 'Ticker' not in df.columns and 'Security Name' in df.columns:
        df['Ticker'] = df['Security Name'].astype(str).str[:10]

    return _standardize(df)
