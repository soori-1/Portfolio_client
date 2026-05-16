# RH Portfolio Reporting Platform

Automated look-through analytics, monthly factsheet generation, and client dashboard for the **Momentum Global ETF Portfolio** at Right Horizons Wealth Management.

## What it does

Given monthly portfolio inputs (weights, returns, commentary), the system:

1. **Fetches** latest holdings for all 13 ETFs from issuer websites
2. **Aggregates** stock-level exposure across the portfolio (look-through)
3. **Computes** sector and country breakdowns using GICS taxonomy
4. **Generates** a 4-page PDF factsheet matching the Right Horizons brand
5. **Updates** a password-protected Streamlit dashboard
6. **Archives** monthly snapshots for historical comparison

## Build status

| Phase | Module | Status |
|-------|--------|--------|
| 1 | Foundation + holdings fetcher | ✅ Built |
| 2 | Look-through engine | ⏳ Next |
| 3 | Performance engine | ⏳ |
| 4 | PDF factsheet | ⏳ |
| 5 | Streamlit dashboard | ⏳ |
| 6 | Historical snapshots | ⏳ |

## Setup

```powershell
# 1. Clone and enter the repo
cd C:\Users\Sooraj\Downloads
git clone https://github.com/soori-1/rh-portfolio-reporting.git
cd rh-portfolio-reporting

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build initial config files
python -m src.build_configs

# 4. (Optional) Edit data/config/portfolio_weights.xlsx if allocations changed
```

## Monthly workflow

```powershell
# 1. Update returns from TradingView
#    - Paste into data/returns/monthly_returns.xlsx
#    - Paste into data/returns/etf_monthly_performance.xlsx

# 2. Write commentary
#    - Create data/commentary/YYYY-MM.md

# 3. Fetch holdings (Phase 1)
python -m src.fetch_holdings

# 4. (Coming Phase 2-4) Generate the report
# python -m src.generate_report --month 2026-05
```

## When a fetcher fails

If the issuer changes their site, the relevant fetcher will fail. You'll see:

```
Holdings fetch failed for:
  EPOL: Could not locate holdings CSV link on ...

Drop manual CSVs in data/holdings/manual/ and re-run.
```

To fix: open the issuer's product page in a browser, click "Download Holdings,"
save the CSV as `data/holdings/manual/EPOL.csv`, and re-run `fetch_holdings`.
The system will use the manual file and cache it for that snapshot date.

## Project structure

```
rh-portfolio-reporting/
├── src/
│   ├── fetchers/                 # iShares / Vanguard / Global X scrapers
│   ├── reports/                  # PDF generation (Phase 4)
│   ├── dashboard/                # Streamlit app (Phase 5)
│   ├── build_configs.py          # One-time config setup
│   └── fetch_holdings.py         # Phase 1 entry point
├── data/
│   ├── config/                   # Editable Excel config files
│   ├── holdings/
│   │   ├── cache/                # Auto-fetched holdings (gitignored)
│   │   └── manual/               # Fallback CSVs when fetchers fail
│   ├── returns/                  # TradingView exports
│   └── commentary/               # Monthly markdown commentary
├── outputs/snapshots/            # Generated reports
└── auth/                         # Login credentials (gitignored)
```

## Configuration files

All in `data/config/`. Edit any of them in Excel:

- **portfolio_weights.xlsx** — the 13 ETFs and their target allocations
- **etf_sources.xlsx** — where to fetch each ETF's holdings from
- **etf_classification.xlsx** — Emerging/Developed/Commodity + Equity/Commodity (for page 2 donuts)
- **sector_overrides.xlsx** — manual sector classifications for unmapped holdings
- **country_overrides.xlsx** — manual country classifications
- **ticker_aliases.xlsx** — Samsung ≡ 005930.KS, etc.
- **report_config.xlsx** — report names, branding, dashboard password
- **disclaimer.txt** — disclaimer text inserted into reports

## Roadmap

Phase 2-6 in build order. Each phase is independent and testable.
