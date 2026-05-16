"""
Export dashboard_data.json for the GitHub Pages HTML dashboard.

Called automatically at the end of generate_report.py.
Can also be run standalone:
    python -m src.export_dashboard_data
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
CONFIG  = ROOT / "data" / "config"
RETURNS = ROOT / "data" / "returns"
OUTPUTS = ROOT / "outputs" / "snapshots"


def export(out_path: Path | None = None) -> Path:
    data = {}

    # ── Config ──
    cfg = pd.read_excel(CONFIG / "report_config.xlsx")
    def g(k, d=""):
        m = cfg[cfg.iloc[:,0].astype(str).str.strip() == k]
        return str(m.iloc[0,1]).strip() if not m.empty else d

    data["portfolio_name"] = g("Portfolio Name", "Momentum Global ETF Portfolio")
    data["benchmark_name"] = g("Benchmark Name", "MSCI ACWI")
    data["company_name"]   = g("Company Name",   "Right Horizons Wealth Management")
    data["tagline"]        = g("Report Tagline", "Guiding you in achieving your goals")

    # ── Latest snapshot ──
    months = sorted([d for d in OUTPUTS.iterdir() if d.is_dir()], reverse=True)
    if not months:
        raise RuntimeError("No snapshots found. Run generate_report first.")
    latest    = months[0]
    month_key = latest.name
    data["month_key"] = month_key
    data["month"]     = pd.to_datetime(month_key + "-01").strftime("%B %Y")
    data["reference_date"] = date.today().strftime("%d %b %Y")

    # ── Monthly returns ──
    ret_path = RETURNS / "monthly_returns.xlsx"
    if ret_path.exists():
        df = pd.read_excel(ret_path)
        df.columns = [c.strip() for c in df.columns]
        for c in df.columns:
            cl = c.lower()
            if "portfolio" in cl: df = df.rename(columns={c: "Port"})
            elif "benchmark" in cl or "acwi" in cl: df = df.rename(columns={c: "Bench"})
        df = df.dropna(subset=["Month"])
        df["Port"]  = pd.to_numeric(df["Port"],  errors="coerce")
        df["Bench"] = pd.to_numeric(df["Bench"], errors="coerce")
        df = df.dropna(subset=["Port","Bench"]).copy()

        cum_p, cum_b = 0.0, 0.0
        monthly = []
        for _, row in df.iterrows():
            cum_p = (1 + cum_p/100) * (1 + row["Port"] /100) * 100 - 100
            cum_b = (1 + cum_b/100) * (1 + row["Bench"]/100) * 100 - 100
            lbl = pd.to_datetime(str(row["Month"]) + "-01").strftime("%b %Y")
            monthly.append({
                "month":   str(row["Month"]),
                "label":   lbl,
                "port":    round(float(row["Port"]),  2),
                "bench":   round(float(row["Bench"]), 2),
                "cum_port":  round(cum_p, 2),
                "cum_bench": round(cum_b, 2),
            })
        data["monthly_returns"] = monthly
        data["ytd_port"]  = round(cum_p, 2)
        data["ytd_bench"] = round(cum_b, 2)
        data["alpha"]     = round(cum_p - cum_b, 2)

    # ── ETF performance ──
    ep_path = RETURNS / "etf_monthly_performance.xlsx"
    if ep_path.exists():
        ep = pd.read_excel(ep_path)
        ep.columns = [c.strip() for c in ep.columns]
        for c in ep.columns:
            cl = c.lower()
            if "ticker" in cl:  ep = ep.rename(columns={c: "Ticker"})
            elif "name" in cl:  ep = ep.rename(columns={c: "Name"})
            elif "return" in cl: ep = ep.rename(columns={c: "Ret"})
        ep["Ret"] = pd.to_numeric(ep.get("Ret", pd.Series()), errors="coerce")
        ep = ep.dropna(subset=["Ret"])
        data["etf_performance"] = [
            {"ticker": str(r["Ticker"]), "name": str(r.get("Name","")), "ret": round(float(r["Ret"]),2)}
            for _, r in ep.iterrows()
        ]

    # ── Look-through ──
    lt = latest / "lookthrough.xlsx"
    if lt.exists():
        # Top holdings
        raw = pd.read_excel(lt, sheet_name="Stock Look-Through", header=None)
        hdr = 0
        for i, row in raw.iterrows():
            if any(str(v).strip() in ("Ticker","Security Name") for v in row.values):
                hdr = i; break
        stocks = pd.read_excel(lt, sheet_name="Stock Look-Through", header=hdr)
        tc = next((c for c in stocks.columns if c.lower() in ("ticker","canonical ticker")), stocks.columns[0])
        top10 = stocks.dropna(subset=[tc]).head(10)
        data["top_holdings"] = [
            {
                "rank":    i+1,
                "ticker":  str(r[tc]),
                "name":    str(r.get("Security Name",""))[:45],
                "sector":  str(r.get("Sector","")),
                "country": str(r.get("Country","")),
                "weight":  round(float(r.get("Portfolio Weight (%)",0)),2),
            }
            for i, (_, r) in enumerate(top10.iterrows())
        ]

        # Sector exposure
        sec = pd.read_excel(lt, sheet_name="Sector Exposure")
        sec_clean = sec[~sec["Sector"].isin(["Unclassified","Diversified","Commodities"])].head(10)
        data["sector_allocation"] = [
            {"name": str(r["Sector"]), "weight": round(float(r["Portfolio Weight (%)"]),1)}
            for _, r in sec_clean.iterrows()
        ]

        # Country exposure
        cty = pd.read_excel(lt, sheet_name="Country Exposure")
        cty_clean = cty[~cty["Country"].isin(["Unknown","Global","Diversified","Unclassified"])].head(10)
        data["country_allocation"] = [
            {"name": str(r["Country"]), "weight": round(float(r["Portfolio Weight (%)"]),1)}
            for _, r in cty_clean.iterrows()
        ]

    # ── Market classification ──
    cls_p = CONFIG / "etf_classification.xlsx"
    wt_p  = CONFIG / "portfolio_weights.xlsx"
    if cls_p.exists() and wt_p.exists():
        cls = pd.read_excel(cls_p)
        wts = pd.read_excel(wt_p).dropna(subset=["ETF Ticker"])
        mg  = wts.merge(cls, left_on="ETF Ticker", right_on="Ticker", how="left")
        bm, bt = {}, {}
        for _, r in mg.iterrows():
            w  = float(r.get("Portfolio Weight (%)", 0) or 0)
            mt = str(r.get("Market Type","Unknown")).strip()
            et = "Commodity ETFs" if str(r.get("ETF Type","")).lower()=="commodity" else "Equity ETFs"
            bm[mt] = bm.get(mt,0)+w
            bt[et] = bt.get(et,0)+w
        data["market_exposure"] = {
            "by_market": [{"name":k,"weight":round(v,1)} for k,v in sorted(bm.items(),key=lambda x:-x[1])],
            "by_type":   [{"name":k,"weight":round(v,1)} for k,v in sorted(bt.items(),key=lambda x:-x[1])],
        }

    # ── ETF weights ──
    if wt_p.exists():
        wdf = pd.read_excel(wt_p).dropna(subset=["ETF Ticker"])
        wdf = wdf[~wdf["ETF Ticker"].astype(str).str.strip().isin(["TOTAL",""])]
        data["portfolio_weights"] = [
            {"ticker": str(r["ETF Ticker"]), "name": str(r.get("ETF Name","")), "weight": round(float(r["Portfolio Weight (%)"]),1)}
            for _, r in wdf.sort_values("Portfolio Weight (%)", ascending=False).iterrows()
        ]

    # ── Commentary ──
    cm = ROOT / "data" / "commentary" / f"{month_key}.md"
    if cm.exists():
        bullets = [l.strip().lstrip("-◆•*#").strip()
                   for l in cm.read_text().splitlines()
                   if l.strip() and not l.strip().startswith("##")]
        data["commentary"] = [b for b in bullets if b][:6]

    # ── Write ──
    if out_path is None:
        out_path = latest / "dashboard_data.json"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"  dashboard_data.json → {out_path}")
    return out_path


if __name__ == "__main__":
    # Also write to repo root for GitHub Pages
    p = export()
    root_copy = ROOT / "dashboard_data.json"
    import shutil
    shutil.copy(p, root_copy)
    print(f"  dashboard_data.json → {root_copy}  (GitHub Pages root)")
