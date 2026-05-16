"""
Right Horizons — Portfolio Admin Dashboard
Run locally: streamlit run admin.py
Admin password: rh_admin_2026 (change before use)
"""
import subprocess
import sys
import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT    = Path(__file__).resolve().parent
CONFIG  = ROOT / "data" / "config"
RETURNS = ROOT / "data" / "returns"
COMMENTARY = ROOT / "data" / "commentary"

# Debug: print paths on startup
import os
os.makedirs(str(CONFIG), exist_ok=True)
os.makedirs(str(RETURNS), exist_ok=True)
os.makedirs(str(COMMENTARY), exist_ok=True)

st.set_page_config(
    page_title="RH Admin — Portfolio Reporting",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Brand CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [data-testid="stAppViewContainer"] {
    background: #F5ECD7 !important;
    font-family: 'IBM Plex Sans', sans-serif;
    color: #2C1810;
}
[data-testid="stAppViewContainer"] .block-container { padding: 2rem 3rem; }
section.main > div { padding-top: 0 !important; }

/* Admin header */
.adm-header {
    border-bottom: 3px solid #8B1A1A;
    padding-bottom: 16px; margin-bottom: 32px;
    display: flex; align-items: center; justify-content: space-between;
}
.adm-title { font-size: 22px; font-weight: 600; color: #8B1A1A; letter-spacing: -0.01em; }
.adm-sub { font-size: 13px; color: #8B6A4A; margin-top: 3px; }
.adm-badge {
    font-size: 10px; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #C8922A;
    border: 1px solid rgba(200,146,42,0.4); padding: 4px 12px;
}

/* Section heads */
.sh {
    font-size: 11px; font-weight: 600; letter-spacing: 0.18em;
    text-transform: uppercase; color: #8B1A1A;
    padding-bottom: 8px; border-bottom: 1px solid rgba(139,26,26,0.2);
    margin: 28px 0 16px;
}
.sh:first-child { margin-top: 0; }

/* Status boxes */
.status-ok { background: #E8F5E9; border-left: 3px solid #2E7D32; padding: 12px 16px; font-size: 13px; color: #1B5E20; margin: 8px 0; }
.status-err { background: #FFEBEE; border-left: 3px solid #C0392B; padding: 12px 16px; font-size: 13px; color: #7B0000; margin: 8px 0; }
.status-info { background: #FFF8E1; border-left: 3px solid #C8922A; padding: 12px 16px; font-size: 13px; color: #5D3A00; margin: 8px 0; }

/* ETF table */
.etf-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }

/* Streamlit overrides */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] select {
    border-radius: 0 !important; border-color: rgba(139,26,26,0.25) !important;
    font-family: 'IBM Plex Mono', monospace !important;
    background: #FFFFFF !important;
}
[data-testid="stButton"] > button {
    background: #8B1A1A !important; color: #F5ECD7 !important;
    border: none !important; border-radius: 0 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 12px !important; font-weight: 600 !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    padding: 10px 28px !important;
}
[data-testid="stButton"] > button:hover { background: #6B1010 !important; }
[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important; color: #8B1A1A !important;
    border: 1px solid #8B1A1A !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: #8B1A1A !important; color: #F5ECD7 !important;
}
.stDownloadButton > button {
    background: transparent !important; color: #8B1A1A !important;
    border: 1px solid #8B1A1A !important; border-radius: 0 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
}
.stDownloadButton > button:hover {
    background: #8B1A1A !important; color: #F5ECD7 !important;
}
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Auth ──────────────────────────────────────────────────────────────────────
ADMIN_PWD = "rh_admin_2026"

def check_auth():
    if st.session_state.get("admin_auth"):
        return True
    st.markdown("""
    <div style="max-width:360px;margin:80px auto;background:#FFFFFF;
         border:1px solid rgba(139,26,26,0.15);padding:36px">
        <div style="font-size:10px;color:#8B6A4A;letter-spacing:0.18em;
             text-transform:uppercase;margin-bottom:4px">Right Horizons</div>
        <div style="font-size:18px;font-weight:600;color:#2C1810;margin-bottom:2px">
             Admin Dashboard</div>
        <div style="font-size:12px;color:#8B6A4A;margin-bottom:24px">
             Internal use only</div>
        <hr style="border:none;border-top:1px solid rgba(139,26,26,0.12);margin-bottom:20px">
    </div>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        pw = st.text_input("", type="password", placeholder="Admin password",
                           label_visibility="collapsed")
        if st.button("Sign In", use_container_width=True):
            if pw == ADMIN_PWD:
                st.session_state["admin_auth"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_portfolio_weights():
    p = CONFIG / "portfolio_weights.xlsx"
    if not p.exists():
        # Try common alternative locations
        for alt in [
            Path.cwd() / "data" / "config" / "portfolio_weights.xlsx",
            Path(__file__).resolve().parent / "data" / "config" / "portfolio_weights.xlsx",
        ]:
            if alt.exists():
                df = pd.read_excel(alt).dropna(subset=["ETF Ticker"])
                return df[~df["ETF Ticker"].astype(str).str.strip().isin(["TOTAL",""])]
        return pd.DataFrame()
    df = pd.read_excel(p).dropna(subset=["ETF Ticker"])
    return df[~df["ETF Ticker"].astype(str).str.strip().isin(["TOTAL",""])]

def load_existing_returns():
    p = RETURNS / "monthly_returns.xlsx"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_excel(p)
    df.columns = [c.strip() for c in df.columns]
    return df

def load_existing_etf_perf():
    p = RETURNS / "etf_monthly_performance.xlsx"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_excel(p)

def month_label(m):
    try:
        return pd.to_datetime(str(m) + "-01").strftime("%B %Y")
    except:
        return str(m)

def run_generate(skip_fetch=False):
    """Run generate_report.py as a subprocess and stream output."""
    import os
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    cmd = [sys.executable, "-m", "src.generate_report"]
    if skip_fetch:
        cmd.append("--skip-fetch")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(ROOT), env=env
    )
    return result.returncode, result.stdout, result.stderr

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not check_auth():
        return

    st.markdown("""
    <div class="adm-header">
        <div>
            <div class="adm-title">⚙ Portfolio Admin Dashboard</div>
            <div class="adm-sub">Right Horizons Wealth Management · Internal Use Only</div>
        </div>
        <div class="adm-badge">Admin Access</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tabs ──
    tabs = st.tabs([
        "📅  Monthly Update",
        "📊  ETF Configuration",
        "🔧  Generate Report",
        "📤  Publish Dashboard",
    ])

    # ══════════════════════════════════════════════════════
    # TAB 1 — Monthly Update
    # ══════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown('<div class="sh">Step 1 — Select Report Month</div>',
                    unsafe_allow_html=True)

        months = pd.date_range("2026-01", periods=24, freq="MS")
        month_options = [d.strftime("%Y-%m") for d in months]
        month_labels  = [d.strftime("%B %Y") for d in months]
        default_idx   = month_options.index(date.today().strftime("%Y-%m")) \
                        if date.today().strftime("%Y-%m") in month_options else 4

        col1, col2 = st.columns([1, 2])
        with col1:
            sel_idx = st.selectbox(
                "Report Month", range(len(month_options)),
                index=default_idx,
                format_func=lambda i: month_labels[i],
                label_visibility="collapsed"
            )
            sel_month = month_options[sel_idx]
            sel_label = month_labels[sel_idx]

        st.markdown(f'<div class="sh">Step 2 — Portfolio vs Benchmark Returns for {sel_label}</div>',
                    unsafe_allow_html=True)

        existing = load_existing_returns()
        ex_row = existing[existing["Month"].astype(str).str.strip() == sel_month] \
                 if not existing.empty else pd.DataFrame()

        c1, c2, c3 = st.columns(3)
        with c1:
            port_ret = st.number_input(
                "Portfolio Return (%)",
                value=float(ex_row.iloc[0,1]) if not ex_row.empty else 0.0,
                step=0.01, format="%.2f"
            )
        with c2:
            bench_ret = st.number_input(
                "Benchmark Return (MSCI ACWI %)",
                value=float(ex_row.iloc[0,2]) if not ex_row.empty else 0.0,
                step=0.01, format="%.2f"
            )
        with c3:
            alpha = port_ret - bench_ret
            color = "#2E7D32" if alpha >= 0 else "#C0392B"
            sign  = "+" if alpha >= 0 else ""
            st.markdown(f"""
            <div style="padding:8px 0">
                <div style="font-size:11px;color:#8B6A4A;letter-spacing:0.1em;
                     text-transform:uppercase;margin-bottom:6px">Alpha</div>
                <div style="font-family:'IBM Plex Mono';font-size:28px;
                     font-weight:500;color:{color}">{sign}{alpha:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f'<div class="sh">Step 3 — ETF Monthly Returns for {sel_label}</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div style="font-size:13px;color:#8B6A4A;margin-bottom:16px">'
            'Enter individual ETF returns from TradingView. Leave blank if unavailable.</div>',
            unsafe_allow_html=True)

        weights = load_portfolio_weights()
        ex_perf = load_existing_etf_perf()

        etf_returns = {}
        if not weights.empty:
            etfs = weights[["ETF Ticker","ETF Name","Portfolio Weight (%)"]].values.tolist()
            cols_per_row = 3
            for i in range(0, len(etfs), cols_per_row):
                row_etfs = etfs[i:i+cols_per_row]
                cols = st.columns(cols_per_row)
                for j, (ticker, name, weight) in enumerate(row_etfs):
                    with cols[j]:
                        # Pre-fill from existing data
                        ex_val = 0.0
                        if not ex_perf.empty:
                            match = ex_perf[ex_perf.iloc[:,0].astype(str).str.strip() == str(ticker)]
                            if not match.empty:
                                try:
                                    ex_val = float(match.iloc[0,2])
                                except:
                                    ex_val = 0.0
                        val = st.number_input(
                            f"{ticker} — {str(name)[:28]} ({weight:.0f}%)",
                            value=ex_val, step=0.01, format="%.2f",
                            key=f"etf_{ticker}"
                        )
                        etf_returns[str(ticker)] = val

        st.markdown(f'<div class="sh">Step 4 — Portfolio Commentary for {sel_label}</div>',
                    unsafe_allow_html=True)

        comm_path = COMMENTARY / f"{sel_month}.md"
        existing_comm = ""
        if comm_path.exists():
            lines = [l.strip().lstrip("-◆•*#").strip()
                     for l in comm_path.read_text().splitlines()
                     if l.strip() and not l.strip().startswith("##")]
            existing_comm = "\n".join([b for b in lines if b])

        st.markdown(
            '<div style="font-size:13px;color:#8B6A4A;margin-bottom:8px">'
            'One bullet point per line. Keep each to 1-2 sentences.</div>',
            unsafe_allow_html=True)
        commentary_text = st.text_area(
            "Commentary", value=existing_comm, height=180,
            label_visibility="collapsed",
            placeholder="Emerging markets outperformed developed markets globally...\nPolish equities were the largest contributor..."
        )

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("💾  Save Monthly Data", key="save_btn"):
            try:
                # Save monthly returns
                df = load_existing_returns().copy()
                if df.empty:
                    df = pd.DataFrame(columns=["Month","Portfolio Return (%)","Benchmark Return (%)"])
                df.columns = ["Month","Portfolio Return (%)","Benchmark Return (%)"]

                # Update or insert row
                mask = df["Month"].astype(str).str.strip() == sel_month
                if mask.any():
                    df.loc[mask, "Portfolio Return (%)"]  = port_ret
                    df.loc[mask, "Benchmark Return (%)"]  = bench_ret
                else:
                    new_row = pd.DataFrame([[sel_month, port_ret, bench_ret]],
                                           columns=df.columns)
                    df = pd.concat([df, new_row], ignore_index=True)
                df = df.sort_values("Month").reset_index(drop=True)
                RETURNS.mkdir(parents=True, exist_ok=True)
                df.to_excel(RETURNS / "monthly_returns.xlsx", index=False)

                # Save ETF performance
                if etf_returns and not weights.empty:
                    etf_rows = []
                    for _, row in weights.iterrows():
                        tk = str(row["ETF Ticker"])
                        etf_rows.append({
                            "ETF Ticker": tk,
                            "ETF Name":   str(row.get("ETF Name","")),
                            "Monthly Return (%)": etf_returns.get(tk, None)
                        })
                    pd.DataFrame(etf_rows).to_excel(
                        RETURNS / "etf_monthly_performance.xlsx", index=False)

                # Save commentary
                if commentary_text.strip():
                    COMMENTARY.mkdir(parents=True, exist_ok=True)
                    bullets = [l.strip() for l in commentary_text.strip().splitlines() if l.strip()]
                    md = f"## Portfolio Highlights — {sel_label}\n\n" + \
                         "\n".join(f"- {b}" for b in bullets)
                    comm_path.write_text(md)

                st.markdown('<div class="status-ok">✓ Monthly data saved successfully.</div>',
                            unsafe_allow_html=True)
                st.cache_data.clear()

            except Exception as e:
                st.markdown(f'<div class="status-err">✗ Save failed: {e}</div>',
                            unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # TAB 2 — ETF Configuration
    # ══════════════════════════════════════════════════════
    with tabs[1]:
        st.markdown('<div class="sh">Current Portfolio Allocation</div>',
                    unsafe_allow_html=True)

        weights = load_portfolio_weights()
        if weights.empty:
            st.warning(f"portfolio_weights.xlsx not found. Looking in: {CONFIG}")
            st.info(f"Current working directory: {Path.cwd()}")
            st.info(f"admin.py location: {ROOT}")
        else:
            total = weights["Portfolio Weight (%)"].sum()
            col1, col2, col3 = st.columns(3)
            col1.metric("ETFs", len(weights))
            col2.metric("Total Weight", f"{total:.1f}%")
            col3.metric("Status", "✓ Valid" if 99 <= total <= 101 else "⚠ Check weights")

            st.dataframe(
                weights[["ETF Ticker","ETF Name","Portfolio Weight (%)"]]\
                .sort_values("Portfolio Weight (%)", ascending=False)\
                .reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown(
                '<div class="status-info">To update: edit <code>data/config/portfolio_weights.xlsx</code> '
                'directly in Excel, then come back here and Generate Report.</div>',
                unsafe_allow_html=True)

        st.markdown('<div class="sh">Auto-Discovery Status</div>', unsafe_allow_html=True)
        ISHARES  = {"EEM","ARTY","IYZ","EPOL","EWT","EWZ","EWA","MCHI","IAU","SLV"}
        GLOBALX  = {"DTCR","LIT","HYDR","COPX","AIQ"}
        INVESCO  = {"TAN","QQQ","RSP"}
        VANGUARD = {"VT","VTI","VOO","VEA","VWO"}
        COMMODITY= {"IAU","SLV","GLD","CPER","PPLT"}
        if not weights.empty:
            rows = []
            for _, r in weights.iterrows():
                tk = str(r["ETF Ticker"]).strip().upper()
                nm = str(r.get("ETF Name",""))
                wt = str(r["Portfolio Weight (%)"]) + "%"
                if tk in COMMODITY:
                    issuer,status = "iShares","🥇 Synthetic (commodity trust)"
                elif tk in ISHARES:
                    issuer,status = "iShares","✓ iShares — direct fetch"
                elif tk in GLOBALX:
                    issuer,status = "GlobalX","✓ GlobalX — direct fetch"
                elif tk in INVESCO:
                    issuer,status = "Invesco","✓ Invesco — direct fetch"
                elif tk in VANGUARD:
                    issuer,status = "Vanguard","📁 Manual CSV required"
                else:
                    issuer,status = "Unknown","⚡ Auto-discover"
                rows.append({"Ticker":tk,"ETF Name":nm[:42],"Weight":wt,"Issuer":issuer,"Status":status})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════
    # TAB 3 — Generate Report
    # ══════════════════════════════════════════════════════
    with tabs[2]:
        st.markdown('<div class="sh">Generate Monthly Report</div>',
                    unsafe_allow_html=True)

        st.markdown("""
        <div class="status-info">
            Clicking Generate will:<br>
            1. Fetch latest holdings for all ETFs (iShares, Vanguard, Global X)<br>
            2. Run look-through analytics (sector, country, stock-level exposure)<br>
            3. Compute performance metrics<br>
            4. Generate the 4-page PDF factsheet<br>
            5. Export <code>dashboard_data.json</code> for the live website
        </div>
        """, unsafe_allow_html=True)

        skip = st.checkbox(
            "Skip fetching (use cached holdings from this month)",
            value=False,
            help="Use this if iShares is rate-limiting or you've already fetched today"
        )

        c1, c2 = st.columns([1, 3])
        with c1:
            generate = st.button("⚡  Generate Report", key="gen_btn")

        if generate:
            with st.spinner("Running pipeline... this takes 2-4 minutes"):
                code, stdout, stderr = run_generate(skip_fetch=skip)

            if code == 0:
                st.markdown('<div class="status-ok">✓ Report generated successfully.</div>',
                            unsafe_allow_html=True)
                with st.expander("View output log"):
                    st.code(stdout)

                # Check for outputs
                snaps = ROOT / "outputs" / "snapshots"
                months_dirs = sorted([d for d in snaps.iterdir() if d.is_dir()], reverse=True)
                if months_dirs:
                    latest = months_dirs[0]
                    pdf = list(latest.glob("*.pdf"))
                    json_f = latest / "dashboard_data.json"

                    st.markdown('<div class="sh">Generated Files</div>',
                                unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        if pdf:
                            st.download_button(
                                "⬇  Download PDF Factsheet",
                                data=pdf[0].read_bytes(),
                                file_name=pdf[0].name,
                                mime="application/pdf",
                                key="dl_pdf"
                            )
                    with col2:
                        if json_f.exists():
                            st.download_button(
                                "⬇  Download dashboard_data.json",
                                data=json_f.read_text(),
                                file_name="dashboard_data.json",
                                mime="application/json",
                                key="dl_json"
                            )
            else:
                st.markdown(f'<div class="status-err">✗ Generation failed.</div>',
                            unsafe_allow_html=True)
                with st.expander("View error log"):
                    st.code(stderr or stdout)

        # Show last generated
        st.markdown('<div class="sh">Last Generated Report</div>', unsafe_allow_html=True)
        snaps = ROOT / "outputs" / "snapshots"
        if snaps.exists():
            months_dirs = sorted([d for d in snaps.iterdir() if d.is_dir()], reverse=True)
            if months_dirs:
                latest = months_dirs[0]
                pdfs = list(latest.glob("*.pdf"))
                json_f = latest / "dashboard_data.json"
                col1, col2, col3 = st.columns(3)
                col1.metric("Month", month_label(latest.name))
                col2.metric("PDF", "✓ Ready" if pdfs else "Not generated")
                col3.metric("Dashboard JSON", "✓ Ready" if json_f.exists() else "Not generated")

                if pdfs or json_f.exists():
                    c1, c2 = st.columns(2)
                    with c1:
                        if pdfs:
                            st.download_button(
                                "⬇  Download PDF",
                                data=pdfs[0].read_bytes(),
                                file_name=pdfs[0].name,
                                mime="application/pdf",
                                key="dl_pdf2"
                            )
                    with c2:
                        if json_f.exists():
                            st.download_button(
                                "⬇  Download dashboard_data.json",
                                data=json_f.read_text(),
                                file_name="dashboard_data.json",
                                mime="application/json",
                                key="dl_json2"
                            )
        else:
            st.info("No reports generated yet.")

    # ══════════════════════════════════════════════════════
    # TAB 4 — Publish Dashboard
    # ══════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown('<div class="sh">Publish to GitHub Pages</div>',
                    unsafe_allow_html=True)

        json_root = ROOT / "dashboard_data.json"

        if json_root.exists():
            data = json.loads(json_root.read_text())
            col1, col2, col3 = st.columns(3)
            col1.metric("Month", data.get("month","—"))
            col2.metric("YTD Return", f"{data.get('ytd_port',0):+.2f}%")
            col3.metric("Alpha", f"{data.get('alpha',0):+.2f}%")

            st.markdown("""
            <div class="status-info" style="margin-top:16px">
                <strong>To publish the updated dashboard:</strong><br><br>
                1. Download <code>dashboard_data.json</code> below<br>
                2. Go to your GitHub repo:
                   <a href="https://github.com/soori-1/Portfolio_client"
                      target="_blank" style="color:#8B1A1A">
                      github.com/soori-1/Portfolio_client</a><br>
                3. Click <code>dashboard_data.json</code> → Edit (pencil icon) →
                   paste the new content → Commit changes<br>
                4. GitHub Pages updates automatically in ~60 seconds<br><br>
                <strong>Live dashboard:</strong>
                <a href="https://soori-1.github.io/Portfolio_client"
                   target="_blank" style="color:#8B1A1A">
                   soori-1.github.io/Portfolio_client</a>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.download_button(
                "⬇  Download dashboard_data.json",
                data=json_root.read_text(),
                file_name="dashboard_data.json",
                mime="application/json",
                key="dl_publish"
            )
        else:
            st.markdown("""
            <div class="status-err">
                dashboard_data.json not found. Go to Generate Report tab and run the pipeline first.
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="sh">Monthly Workflow</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:14px;color:#2C1810;line-height:2">
            <span style="color:#8B1A1A;font-weight:600">1.</span>
            Monthly Update tab → Enter portfolio return, benchmark return, ETF returns, commentary → Save<br>
            <span style="color:#8B1A1A;font-weight:600">2.</span>
            Generate Report tab → Click Generate (2-4 min)<br>
            <span style="color:#8B1A1A;font-weight:600">3.</span>
            Publish tab → Download <code>dashboard_data.json</code><br>
            <span style="color:#8B1A1A;font-weight:600">4.</span>
            Update the file on GitHub → live site refreshes in 60 seconds<br>
            <span style="color:#8B1A1A;font-weight:600">5.</span>
            Download PDF → send to clients or upload to Documents section
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
