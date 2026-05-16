"""
Right Horizons — Momentum Global ETF Portfolio Dashboard
Institutional-grade, clean, data-forward. Cream/maroon/gold palette.
"""
import base64
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="RH Momentum Global",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Palette ──────────────────────────────────────────────────────────────────
M  = "#8B1A1A"   # maroon
G  = "#C8922A"   # gold
BG = "#F5ECD7"   # cream
S  = "#FFFFFF"   # surface
S2 = "#EDE2C8"   # cream-dark
TX = "#2C1810"   # text
MU = "#8B6A4A"   # muted
GR = "#2E7D32"   # positive
RD = "#C0392B"   # negative
BD = "rgba(139,26,26,0.12)"  # border

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800;900&family=Inter:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #F5ECD7 !important;
    font-family: 'Inter', sans-serif; font-size: 15px;
    color: #2C1810;
    font-size: 14px;
}
section.main > div { padding-top: 0 !important; }
[data-testid="stAppViewContainer"] > .main > div { padding-top: 0 !important; }
[data-testid="stAppViewContainer"] .block-container { padding: 0 2rem 2rem; }

/* ── Fund header ── */
.fund-header {
    padding: 32px 0 24px;
    border-bottom: 3px solid #8B1A1A;
    margin-bottom: 32px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
}
.fund-name {
    font-family: 'Inter', sans-serif; font-size: 15px;
    font-size: 22px; font-weight: 600;
    color: #8B1A1A; letter-spacing: -0.01em;
    line-height: 1.2;
}
.fund-meta {
    font-size: 14px; color: #8B6A4A;
    margin-top: 4px; letter-spacing: 0.02em;
}
.fund-ytd {
    text-align: right;
}
.fund-ytd-val {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 30px; font-weight: 500; line-height: 1;
}
.fund-ytd-label {
    font-size: 13px; color: #8B6A4A;
    letter-spacing: 0.08em; text-transform: uppercase;
    margin-top: 3px;
}

/* ── Section headers ── */
.sh {
    font-size: 13px; font-weight: 700;
    color: #8B1A1A; text-transform: uppercase;
    letter-spacing: 0.14em;
    padding-bottom: 9px;
    border-bottom: 2px solid rgba(139,26,26,0.2);
    margin: 32px 0 18px;
}

/* ── Key facts table ── */
.kf { width: 100%; border-collapse: collapse; font-size: 14px; background: #FFFFFF; }
.kf tr { border-bottom: 1px solid rgba(139,26,26,0.08); }
.kf tr:first-child td { padding-top: 12px; }
.kf td { padding: 7px 0; vertical-align: top; }
.kf .kf-label { color: #8B6A4A; width: 52%; font-size: 14px; }
.kf .kf-val { color: #2C1810; font-weight: 600; font-family: 'IBM Plex Mono', monospace; font-size: 14px; }

/* ── Performance table ── */
.pt { width: 100%; border-collapse: collapse; font-size: 11px; font-family: 'IBM Plex Mono', monospace; }
.pt thead tr { border-bottom: 2px solid #8B1A1A; }
.pt th {
    padding: 10px 16px 10px 0; text-align: right;
    font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
    color: #8B6A4A; font-weight: 600; font-family: 'Inter', sans-serif;
}
.pt th:first-child { text-align: left; }
.pt td { padding: 10px 16px 10px 0; text-align: right; border-bottom: 1px solid rgba(139,26,26,0.07); font-size: 13px; }
.pt td:first-child { text-align: left; color: #8B6A4A; font-size: 13px; }
.pt tr.ytd td { border-top: 2px solid #C8922A; border-bottom: none; font-weight: 600; }
.pt tr.ytd td:first-child { color: #2C1810; }
.pos { color: #2E7D32; }
.neg { color: #C0392B; }

/* ── Holdings table ── */
.ht { width: 100%; border-collapse: collapse; font-size: 11px; }
.ht thead tr { border-bottom: 2px solid #8B1A1A; }
.ht th {
    padding: 10px 12px 10px 0; text-align: left;
    font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
    color: #8B6A4A; font-weight: 600;
}
.ht th.r { text-align: right; }
.ht td { padding: 10px 12px 10px 0; border-bottom: 1px solid rgba(139,26,26,0.07); font-size: 13px; }
.ht .rank { color: #8B6A4A; font-size: 10px; width: 24px; font-family: 'IBM Plex Mono', monospace; }
.ht .tk { color: #8B1A1A; font-weight: 600; font-family: 'IBM Plex Mono', monospace; }
.ht .nm { color: #2C1810; }
.ht .sc { color: #8B6A4A; font-size: 10px; }
.ht .wt { text-align: right; font-family: 'IBM Plex Mono', monospace; font-weight: 500; }
.ht tr.total td { border-top: 1px solid rgba(139,26,26,0.25); border-bottom: none; font-weight: 600; }

/* ── Allocation table (Bloomberg-style) ── */
.at { width: 100%; border-collapse: collapse; font-size: 11px; }
.at thead tr { border-bottom: 2px solid #8B1A1A; }
.at th {
    padding: 10px 0 10px; text-align: left;
    font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase;
    color: #8B6A4A; font-weight: 600;
}
.at th.r { text-align: right; }
.at td { padding: 6px 0; border-bottom: 1px solid rgba(139,26,26,0.07); vertical-align: middle; }
.at .nm { color: #2C1810; font-size: 14px; width: 38%; }
.at .bar-cell { width: 44%; padding-right: 12px; }
.at .bar-bg { background: rgba(139,26,26,0.08); height: 6px; border-radius: 0; }
.at .bar-fill { background: #8B1A1A; height: 6px; border-radius: 0; }
.at .wt { text-align: right; font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 14px; width: 18%; }

/* ── Best/Worst ── */
.bw-section { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.bw-block {}
.bw-label {
    font-size: 9px; font-weight: 600; letter-spacing: 0.16em;
    text-transform: uppercase; color: #8B6A4A; margin-bottom: 8px;
    padding-bottom: 6px; border-bottom: 1px solid rgba(139,26,26,0.15);
}
.bw-row {
    display: flex; align-items: baseline; padding: 8px 0;
    border-bottom: 1px solid rgba(139,26,26,0.06); font-size: 11px;
}
.bw-row:last-child { border-bottom: none; }
.bw-tk { color: #8B1A1A; font-weight: 700; font-family: 'IBM Plex Mono', monospace; min-width: 56px; font-size: 14px; }
.bw-nm { flex: 1; color: #8B6A4A; font-size: 13px; padding: 0 10px; }
.bw-ret { font-family: 'IBM Plex Mono', monospace; font-weight: 500; font-size: 13px; }

/* ── Commentary ── */
.comm { border-left: 2px solid #C8922A; padding: 4px 0 4px 18px; }
.comm-row { display: flex; gap: 10px; margin-bottom: 14px; font-size: 14px; line-height: 1.65; color: #2C1810; }
.comm-row:last-child { margin-bottom: 0; }
.comm-dia { color: #C8922A; flex-shrink: 0; padding-top: 3px; font-size: 8px; }

/* ── Framework boxes ── */
.fw-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; margin-top: 12px; }
.fw-box {
    border: 1px solid rgba(200,146,42,0.4);
    padding: 18px 16px 14px;
    background: #FFFFFF;
}
.fw-box-title {
    font-size: 9px; font-weight: 600; letter-spacing: 0.18em;
    text-transform: uppercase; color: #8B6A4A; margin-bottom: 4px;
}
.fw-box-range {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px; font-weight: 500; color: #8B1A1A; margin-bottom: 10px;
}
.fw-box-subtitle {
    font-size: 13px; font-weight: 600; color: #2C1810; margin-bottom: 8px;
}
.fw-box-body { font-size: 12px; color: #8B6A4A; line-height: 1.65; }
.fw-tag {
    display: inline-block; margin-top: 12px;
    font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase;
    color: #C8922A; border: 1px solid rgba(200,146,42,0.5);
    padding: 3px 10px;
}

/* ── Allocation strategy ── */
.as-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px; }
.as-phase { text-align: center; }
.as-label {
    font-size: 9px; font-weight: 600; letter-spacing: 0.14em;
    text-transform: uppercase; color: #8B6A4A; margin-bottom: 8px;
}
.as-box {
    border: 1px solid rgba(200,146,42,0.4);
    padding: 12px 10px; background: #FFFFFF;
    font-size: 11px; font-weight: 500; color: #2C1810;
    text-align: center; line-height: 1.5;
}
.as-connector {
    height: 2px; background: rgba(139,26,26,0.15);
    margin: 16px 0; position: relative;
}

/* ── Streamlit overrides ── */
[data-testid="stTabs"] button {
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important; font-weight: 500 !important;
    color: #8B6A4A !important; letter-spacing: 0.04em !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #8B1A1A !important;
}
.stDownloadButton > button {
    background: transparent !important;
    border: 1px solid #8B1A1A !important;
    color: #8B1A1A !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 12px !important; font-weight: 500 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    border-radius: 0 !important; padding: 10px 24px !important;
}
.stDownloadButton > button:hover {
    background: #8B1A1A !important; color: #F5ECD7 !important;
}
[data-testid="stSidebar"] { background: linear-gradient(180deg,#8B1A1A,#6B1010); border-right:2px solid #A8741A; }
[data-testid="stSidebar"] * { color: #F5ECD7 !important; }
[data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"] { background:#C8922A !important; color:#2C1810 !important; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Auth ──────────────────────────────────────────────────────────────────────
def check_password():
    try:
        pwd = st.secrets.get("dashboard_password", "rh2026")
    except Exception:
        pwd = "rh2026"
    if st.session_state.get("auth"):
        return True

    _, col, _ = st.columns([1.2, 1, 1.2])
    with col:
        st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
        root = Path(__file__).resolve().parent
        for p in [root / "assets" / "logo.png", root.parent / "assets" / "logo.png"]:
            if p.exists():
                b64 = base64.b64encode(p.read_bytes()).decode()
                st.markdown(
                    '<img src="data:image/png;base64,' + b64 +
                    '" style="height:36px;margin-bottom:24px;display:block">',
                    unsafe_allow_html=True)
                break

        st.markdown("""
        <div style="font-size:10px;color:#8B6A4A;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:2px">
            Right Horizons Wealth Management</div>
        <div style="font-size:17px;font-weight:600;color:#2C1810;margin-bottom:2px">
            Momentum Global ETF Portfolio</div>
        <div style="font-size:10px;color:#8B6A4A;margin-bottom:24px">
            Client Dashboard</div>
        <hr style="border:none;border-top:1px solid rgba(139,26,26,0.15);margin-bottom:20px">
        """, unsafe_allow_html=True)

        pw = st.text_input("", type="password", placeholder="Password",
                           label_visibility="collapsed")
        if st.button("Sign In", use_container_width=True):
            if pw == pwd:
                st.session_state["auth"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    root = Path(__file__).resolve().parent
    snaps = root / "outputs" / "snapshots"
    if not snaps.exists():
        return None
    months = sorted([d for d in snaps.iterdir() if d.is_dir()], reverse=True)
    if not months:
        return None
    latest = months[0]
    d = {"month_key": latest.name,
         "month": pd.to_datetime(latest.name + "-01").strftime("%B %Y")}

    cfg_p = root / "data" / "config" / "report_config.xlsx"
    if cfg_p.exists():
        cfg = pd.read_excel(cfg_p)
        def g(k, dv=""):
            m = cfg[cfg.iloc[:,0].astype(str).str.strip() == k]
            return str(m.iloc[0,1]).strip() if not m.empty else dv
        d["name"]  = g("Portfolio Name","Momentum Global ETF Portfolio")
        d["bench"] = g("Benchmark Name","MSCI ACWI")
        d["co"]    = g("Company Name","Right Horizons Wealth Management")

    ret = root / "data" / "returns"
    if (ret / "monthly_returns.xlsx").exists():
        df = pd.read_excel(ret / "monthly_returns.xlsx")
        df.columns = [c.strip() for c in df.columns]
        for c in df.columns:
            cl = c.lower()
            if "portfolio" in cl: df = df.rename(columns={c:"Port"})
            elif "benchmark" in cl or "acwi" in cl: df = df.rename(columns={c:"Bench"})
        df = df.dropna(subset=["Month"])
        df["Port"]  = pd.to_numeric(df["Port"],  errors="coerce")
        df["Bench"] = pd.to_numeric(df["Bench"], errors="coerce")
        df = df.dropna(subset=["Port","Bench"]).copy()
        df["Cum_P"] = ((1+df["Port"] /100).cumprod()-1)*100
        df["Cum_B"] = ((1+df["Bench"]/100).cumprod()-1)*100
        df["Lbl"]   = df["Month"].apply(lambda m: pd.to_datetime(str(m)+"-01").strftime("%b %Y"))
        d["monthly"] = df

    if (ret / "etf_monthly_performance.xlsx").exists():
        ep = pd.read_excel(ret / "etf_monthly_performance.xlsx")
        ep.columns = [c.strip() for c in ep.columns]
        for c in ep.columns:
            cl = c.lower()
            if "ticker" in cl:  ep = ep.rename(columns={c:"Ticker"})
            elif "name" in cl:  ep = ep.rename(columns={c:"Name"})
            elif "return" in cl: ep = ep.rename(columns={c:"Ret"})
        ep["Ret"] = pd.to_numeric(ep.get("Ret",pd.Series()), errors="coerce")
        d["etf_perf"] = ep.dropna(subset=["Ret"])

    lt = latest / "lookthrough.xlsx"
    if lt.exists():
        raw = pd.read_excel(lt, sheet_name="Stock Look-Through", header=None)
        hdr = 0
        for i, row in raw.iterrows():
            if any(str(v).strip() in ("Ticker","Security Name") for v in row.values):
                hdr = i; break
        d["stocks"]    = pd.read_excel(lt, sheet_name="Stock Look-Through", header=hdr)
        d["sectors"]   = pd.read_excel(lt, sheet_name="Sector Exposure")
        d["countries"] = pd.read_excel(lt, sheet_name="Country Exposure")

    cm = root / "data" / "commentary" / f"{latest.name}.md"
    if cm.exists():
        bl = [l.strip().lstrip("-◆•*#").strip()
              for l in cm.read_text().splitlines()
              if l.strip() and not l.strip().startswith("##")]
        d["commentary"] = [b for b in bl if b][:6]

    pdf = latest / f"RH_MomentumGlobal_{latest.name}.pdf"
    if pdf.exists():
        d["pdf_bytes"] = pdf.read_bytes()
        d["pdf_name"]  = pdf.name

    cls_p = root / "data" / "config" / "etf_classification.xlsx"
    wt_p  = root / "data" / "config" / "portfolio_weights.xlsx"
    if cls_p.exists() and wt_p.exists():
        cls = pd.read_excel(cls_p)
        wts = pd.read_excel(wt_p).dropna(subset=["ETF Ticker"])
        mg  = wts.merge(cls, left_on="ETF Ticker", right_on="Ticker", how="left")
        bm, bt = {}, {}
        for _, r in mg.iterrows():
            w  = float(r.get("Portfolio Weight (%)",0) or 0)
            mt = str(r.get("Market Type","Unknown")).strip()
            et = "Commodity ETFs" if str(r.get("ETF Type","")).lower()=="commodity" else "Equity ETFs"
            bm[mt] = bm.get(mt,0)+w
            bt[et] = bt.get(et,0)+w
        d["by_market"] = {k:round(v,1) for k,v in sorted(bm.items(),key=lambda x:-x[1])}
        d["by_type"]   = {k:round(v,1) for k,v in sorted(bt.items(),key=lambda x:-x[1])}

    return d


# ── Chart helpers ─────────────────────────────────────────────────────────────
BASE = dict(
    plot_bgcolor=BG, paper_bgcolor=BG,
    font=dict(family="IBM Plex Mono", color=MU, size=12),
    hoverlabel=dict(bgcolor=S, bordercolor=M,
                    font=dict(family="IBM Plex Mono", color=TX)),
)

def chart_ytd(df, bench_name):
    x  = [""] + list(df["Lbl"])
    yp = [0]  + list(df["Cum_P"])
    yb = [0]  + list(df["Cum_B"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=yb, name=bench_name,
        line=dict(color=G, width=1.8, dash="dot"), mode="lines"))
    fig.add_trace(go.Scatter(x=x, y=yp, name="Portfolio",
        line=dict(color=M, width=2.2), mode="lines"))
    for val, color, nm in [(yp[-1],M,"Portfolio"),(yb[-1],G,bench_name)]:
        s = "+" if val>=0 else ""
        fig.add_annotation(x=x[-1], y=val,
            text="<b>"+s+f"{val:.2f}%</b>",
            showarrow=False, xanchor="left", xshift=10,
            font=dict(color=color, size=11, family="IBM Plex Mono"))
    fig.update_layout(**BASE, height=300,
        margin=dict(l=0,r=72,t=16,b=0),
        legend=dict(orientation="h", y=1.06, x=0, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(ticksuffix="%", gridcolor="rgba(139,26,26,0.08)",
                   zeroline=True, zerolinecolor="rgba(139,26,26,0.2)",
                   zerolinewidth=1),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", showline=False))
    return fig

def chart_bars(df, bench_name):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Lbl"], y=df["Port"], name="Portfolio",
        marker_color=M, width=0.35,
        text=[f"{v:+.1f}%" for v in df["Port"]],
        textposition="outside", textfont=dict(size=9,color=M)))
    fig.add_trace(go.Bar(x=df["Lbl"], y=df["Bench"], name=bench_name,
        marker_color=G, width=0.35,
        text=[f"{v:+.1f}%" for v in df["Bench"]],
        textposition="outside", textfont=dict(size=9,color=G)))
    fig.update_layout(**BASE, height=280, barmode="group",
        margin=dict(l=0,r=0,t=24,b=0),
        legend=dict(orientation="h", y=1.08, x=0, font=dict(size=10),
                    bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(ticksuffix="%", gridcolor="rgba(139,26,26,0.08)",
                   zeroline=True, zerolinecolor="rgba(139,26,26,0.2)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"))
    return fig


def chart_donut(labels, values, colors, title=""):
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.58,
        marker=dict(colors=colors, line=dict(color=BG, width=2)),
        textinfo="none",
        hovertemplate="%{label}: <b>%{value:.1f}%</b><extra></extra>"))
    fig.update_layout(**BASE, height=220,
        margin=dict(l=0,r=0,t=8,b=8),
        showlegend=True,
        legend=dict(
            orientation="v", x=1.0, y=0.5,
            font=dict(size=12, family="IBM Plex Mono"),
            itemsizing="constant",
        ))
    if title:
        fig.add_annotation(text=title, x=0.5, y=0.5, showarrow=False,
            font=dict(size=11, color=MU, family="IBM Plex Mono"),
            xanchor="center", yanchor="middle")
    return fig


# ── HTML helpers ──────────────────────────────────────────────────────────────
def sfmt(v):
    if pd.isna(v): return "—"
    s = f"+{v:.2f}%" if v>=0 else f"{v:.2f}%"
    return f'<span class="{"pos" if v>=0 else "neg"}">{s}</span>'

def alloc_table(df, name_col, max_w=None):
    clean = df[~df[name_col].isin(
        ["Unclassified","Diversified","Unknown","Global","Commodities"])].head(10)
    if max_w is None:
        max_w = clean["Portfolio Weight (%)"].max() or 1
    rows = ""
    for _, r in clean.iterrows():
        w   = float(r["Portfolio Weight (%)"])
        pct = min(w / max_w * 100, 100)
        rows += (
            f'<tr><td class="nm">{r[name_col]}</td>'
            f'<td class="bar-cell">'
            f'<div class="bar-bg"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
            f'</td>'
            f'<td class="wt">{w:.1f}%</td></tr>'
        )
    return f'<table class="at"><thead><tr><th>{name_col}</th><th></th><th class="r">Weight</th></tr></thead><tbody>{rows}</tbody></table>'


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not check_password():
        return

    d = load_data()
    if not d:
        st.error("No snapshot data found. Run `python -m src.generate_report` first.")
        return

    monthly  = d.get("monthly")
    etf_p    = d.get("etf_perf")
    stocks   = d.get("stocks")
    sectors  = d.get("sectors")
    countries= d.get("countries")
    month    = d.get("month","")
    name     = d.get("name","Momentum Global ETF Portfolio")
    bench    = d.get("bench","MSCI ACWI")
    co       = d.get("co","Right Horizons Wealth Management")

    ytd_p = round(monthly["Cum_P"].iloc[-1], 2) if monthly is not None else 0
    ytd_b = round(monthly["Cum_B"].iloc[-1], 2) if monthly is not None else 0
    alpha = round(ytd_p - ytd_b, 2)
    last_m = monthly["Lbl"].iloc[-1] if monthly is not None else month

    # ── Logo ──
    root = Path(__file__).resolve().parent
    for p in [root/"assets"/"logo.png", root.parent/"assets"/"logo.png"]:
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode()
            st.markdown(
                '<div style="padding:20px 0 0">'
                '<img src="data:image/png;base64,' + b64 +
                '" style="height:32px"></div>',
                unsafe_allow_html=True)
            break

    # ── Fund header ──
    ytd_color = GR if ytd_p >= 0 else RD
    ytd_sign  = "+" if ytd_p >= 0 else ""
    st.markdown(
        '<div class="fund-header">'
        '<div>'
        '<div class="fund-name">' + name + '</div>'
        '<div class="fund-meta">' + co + '  ·  Monthly Report  ·  ' + month + '  ·  13 ETF Holdings</div>'
        '</div>'
        '<div class="fund-ytd">'
        '<div class="fund-ytd-val" style="color:' + ytd_color + '">' +
        ytd_sign + f'{ytd_p:.2f}%</div>'
        '<div class="fund-ytd-label">YTD Return  ·  vs ' +
        bench + ' ' + (("+" if alpha>=0 else "") + f"{alpha:.2f}%") +
        '</div></div></div>',
        unsafe_allow_html=True)

    # ── Tabs ──
    tabs = st.tabs(["Overview", "Performance", "Portfolio", "Strategy", "Documents"])

    # ════════════════════════════════════════════════════════
    # TAB 1 — Overview
    # ════════════════════════════════════════════════════════
    with tabs[0]:
        col1, col2 = st.columns([1, 1.8])

        with col1:
            st.markdown('<div class="sh">Key Facts</div>', unsafe_allow_html=True)
            bm_str = "  ·  ".join(f"{k} {v:.1f}%" for k,v in d.get("by_market",{}).items())
            kf_rows = [
                ("Reference Date",    last_m),
                ("Number of Holdings","13 ETFs"),
                ("Benchmark",         bench),
                ("Emerging Markets",  f"{d.get('by_market',{}).get('Emerging Markets',0):.1f}%"),
                ("Developed Markets", f"{d.get('by_market',{}).get('Developed Markets',0):.1f}%"),
                ("Commodity",         f"{d.get('by_market',{}).get('Commodity',0):.1f}%"),
                ("Equity ETFs",       f"{d.get('by_type',{}).get('Equity ETFs',0):.1f}%"),
            ]
            rows = "".join(
                f'<tr><td class="kf-label">{k}</td><td class="kf-val">{v}</td></tr>'
                for k,v in kf_rows
            )
            st.markdown(f'<table class="kf">{rows}</table>', unsafe_allow_html=True)

            if d.get("commentary"):
                st.markdown('<div class="sh">Portfolio Highlights</div>', unsafe_allow_html=True)
                items = "".join(
                    '<div class="comm-row"><span class="comm-dia">▪</span>'
                    f'<span>{b}</span></div>' for b in d["commentary"]
                )
                st.markdown(f'<div class="comm">{items}</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="sh">Cumulative YTD Performance</div>', unsafe_allow_html=True)
            if monthly is not None:
                st.plotly_chart(chart_ytd(monthly, bench),
                                use_container_width=True,
                                config={"displayModeBar": False}, key="ytd_overview")

            if etf_p is not None and len(etf_p) >= 2:
                st.markdown(f'<div class="sh">Best & Worst Performers — {last_m}</div>',
                            unsafe_allow_html=True)
                top3 = etf_p.nlargest(3,"Ret")
                bot3 = etf_p.nsmallest(3,"Ret")
                c1, c2 = st.columns(2)
                for col, df_, lbl in [(c1,top3,"Top Gainers"),(c2,bot3,"Laggards")]:
                    with col:
                        rows = ""
                        for _, r in df_.iterrows():
                            ret = r["Ret"]
                            clr = GR if ret>=0 else RD
                            s   = "+" if ret>=0 else ""
                            rows += (
                                f'<div class="bw-row">'
                                f'<span class="bw-tk">{r["Ticker"]}</span>'
                                f'<span class="bw-nm">{str(r.get("Name",""))[:36]}</span>'
                                f'<span class="bw-ret" style="color:{clr}">({s}{ret:.2f}%)</span>'
                                f'</div>'
                            )
                        st.markdown(
                            f'<div class="bw-block"><div class="bw-label">{lbl}</div>{rows}</div>',
                            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # TAB 2 — Performance
    # ════════════════════════════════════════════════════════
    with tabs[1]:
        if monthly is None:
            st.info("No performance data loaded.")
        else:
            st.markdown('<div class="sh">Monthly Returns vs Benchmark</div>', unsafe_allow_html=True)
            t1, t2 = st.tabs(["Cumulative", "Monthly"])
            with t1:
                st.plotly_chart(chart_ytd(monthly, bench),
                                use_container_width=True, config={"displayModeBar":False}, key="ytd_perf")
            with t2:
                st.plotly_chart(chart_bars(monthly, bench),
                                use_container_width=True, config={"displayModeBar":False}, key="bars_perf")

            st.markdown('<div class="sh">Returns Table</div>', unsafe_allow_html=True)
            ytd_pv = monthly["Cum_P"].iloc[-1]
            ytd_bv = monthly["Cum_B"].iloc[-1]
            rows = ""
            for _, r in monthly.iterrows():
                rows += (f'<tr><td>{r["Lbl"]}</td>'
                         f'<td>{sfmt(r["Port"])}</td>'
                         f'<td>{sfmt(r["Bench"])}</td>'
                         f'<td>{sfmt(r["Port"]-r["Bench"])}</td></tr>')
            rows += (f'<tr class="ytd"><td><strong>YTD Cumulative</strong></td>'
                     f'<td>{sfmt(ytd_pv)}</td>'
                     f'<td>{sfmt(ytd_bv)}</td>'
                     f'<td>{sfmt(ytd_pv-ytd_bv)}</td></tr>')
            st.markdown(
                f'<table class="pt"><thead><tr>'
                f'<th>Month</th><th style="text-align:right">Portfolio %</th>'
                f'<th style="text-align:right">{bench} %</th>'
                f'<th style="text-align:right">Outperformance</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>',
                unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # TAB 3 — Portfolio
    # ════════════════════════════════════════════════════════
    with tabs[2]:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="sh">Top 10 Holdings</div>', unsafe_allow_html=True)
            if stocks is not None:
                tc = next((c for c in stocks.columns
                           if c.lower() in ("ticker","canonical ticker")), stocks.columns[0])
                top10 = stocks.dropna(subset=[tc]).head(10)
                rows = ""
                for i,(_, r) in enumerate(top10.iterrows(), 1):
                    rows += (f'<tr>'
                             f'<td class="rank">{i}</td>'
                             f'<td class="tk">{r[tc]}</td>'
                             f'<td class="nm">{str(r.get("Security Name",""))[:32]}</td>'
                             f'<td class="sc">{r.get("Country","")}</td>'
                             f'<td class="wt">{float(r.get("Portfolio Weight (%)",0)):.2f}%</td>'
                             f'</tr>')
                total = top10["Portfolio Weight (%)"].sum()
                rows += (f'<tr class="total">'
                         f'<td colspan="4" style="text-align:right;font-size:10px;color:#8B6A4A">Top 10 Total</td>'
                         f'<td class="wt">{total:.2f}%</td></tr>')
                st.markdown(
                    f'<table class="ht"><thead><tr>'
                    f'<th>#</th><th>Ticker</th><th>Security</th>'
                    f'<th>Country</th><th class="r">Weight</th>'
                    f'</tr></thead><tbody>{rows}</tbody></table>',
                    unsafe_allow_html=True)

        with col2:
            if sectors is not None:
                st.markdown('<div class="sh">Sector Allocation</div>', unsafe_allow_html=True)
                # Donut
                sec_clean = sectors[~sectors["Sector"].isin(["Unclassified","Diversified","Commodities"])].head(8)
                if len(sec_clean) > 0:
                    st.plotly_chart(
                        chart_donut(
                            list(sec_clean["Sector"]),
                            list(sec_clean["Portfolio Weight (%)"]),
                            [M, G, MU, "#5C8A4A", "#2E6B8A", "#8A4A6B", "#6B6B2E", "#2E8A6B"][:len(sec_clean)]),
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key="donut_sector")
                st.markdown(alloc_table(sectors, "Sector"), unsafe_allow_html=True)

        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        col3, col4 = st.columns(2)

        with col3:
            if countries is not None:
                st.markdown('<div class="sh">Country Allocation</div>', unsafe_allow_html=True)
                # Donut
                cty_clean = countries[~countries["Country"].isin(["Unknown","Global","Diversified"])].head(8)
                if len(cty_clean) > 0:
                    st.plotly_chart(
                        chart_donut(
                            list(cty_clean["Country"]),
                            list(cty_clean["Portfolio Weight (%)"]),
                            [M, G, MU, "#5C8A4A", "#2E6B8A", "#8A4A6B", "#6B6B2E", "#2E8A6B"][:len(cty_clean)]),
                        use_container_width=True,
                        config={"displayModeBar": False},
                        key="donut_country")
                st.markdown(alloc_table(countries, "Country"), unsafe_allow_html=True)

        with col4:
            if d.get("by_market"):
                st.markdown('<div class="sh">Market Classification</div>', unsafe_allow_html=True)
                bm = d["by_market"]
                max_w = max(bm.values()) if bm else 1
                rows = ""
                for k, v in bm.items():
                    pct = min(v/max_w*100, 100)
                    rows += (f'<tr><td class="nm">{k}</td>'
                             f'<td class="bar-cell">'
                             f'<div class="bar-bg"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
                             f'</td><td class="wt">{v:.1f}%</td></tr>')
                bt = d.get("by_type", {})
                if bt:
                    rows += '<tr><td colspan="3" style="padding-top:12px;font-size:9px;color:#8B6A4A;text-transform:uppercase;letter-spacing:0.1em">ETF Type</td></tr>'
                    max_bt = max(bt.values()) if bt else 1
                    for k, v in bt.items():
                        pct = min(v/max_bt*100, 100)
                        rows += (f'<tr><td class="nm">{k}</td>'
                                 f'<td class="bar-cell">'
                                 f'<div class="bar-bg"><div class="bar-fill" style="background:#C8922A;width:{pct:.1f}%"></div></div>'
                                 f'</td><td class="wt">{v:.1f}%</td></tr>')
                st.markdown(
                    f'<table class="at"><thead><tr><th>Classification</th><th></th><th class="r">Weight</th></tr></thead>'
                    f'<tbody>{rows}</tbody></table>',
                    unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # TAB 4 — Strategy
    # ════════════════════════════════════════════════════════
    with tabs[3]:
        st.markdown('<div class="sh">Portfolio Framework</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="fw-grid">
            <div class="fw-box">
                <div class="fw-box-title">Core</div>
                <div class="fw-box-range">30 – 50%</div>
                <div class="fw-box-subtitle">Consistency & Risk Control</div>
                <div class="fw-box-body">Focus towards diverse global equity. High-quality fixed income and low-volatility strategies. Stability anchor for the portfolio across all market regimes.</div>
                <div class="fw-tag">Stability Anchor</div>
            </div>
            <div class="fw-box">
                <div class="fw-box-title">Momentum</div>
                <div class="fw-box-range">30 – 50%</div>
                <div class="fw-box-subtitle">Tactical Alpha & Cycle Capture</div>
                <div class="fw-box-body">Trend-following, sector rotation, factor tilts. Actively rebalanced with macro regime signals to capture alpha across market cycles.</div>
                <div class="fw-tag">Alpha Engine</div>
            </div>
            <div class="fw-box">
                <div class="fw-box-title">Aggressive</div>
                <div class="fw-box-range">0 – 30%</div>
                <div class="fw-box-subtitle">High-Conviction Outperformance</div>
                <div class="fw-box-body">Concentrated high-upside positions. Growth equities, satellite alternatives, special situations. Sized dynamically with market conviction.</div>
                <div class="fw-tag">Return Booster</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sh" style="margin-top:36px">Allocation Strategy — Market Cycle</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:11px;color:#8B6A4A;margin-bottom:16px">
            Dynamic allocation across market cycles — Early Expansion through Contraction
        </div>
        <div class="as-grid">
            <div class="as-phase">
                <div class="as-label">Early Expansion</div>
                <div class="as-box">Momentum<br>+ Aggressive</div>
            </div>
            <div class="as-phase">
                <div class="as-label">Mid Cycle</div>
                <div class="as-box">Balanced</div>
            </div>
            <div class="as-phase">
                <div class="as-label">Late Cycle</div>
                <div class="as-box">Core +<br>Momentum</div>
            </div>
            <div class="as-phase">
                <div class="as-label">Contraction</div>
                <div class="as-box">Increase Core<br>+ Increase Cash</div>
            </div>
        </div>
        <div style="margin:20px 0 8px;height:2px;background:linear-gradient(90deg,rgba(139,26,26,0.3),rgba(200,146,42,0.3));"></div>
        <div style="display:flex;justify-content:space-between;font-size:9px;color:#8B6A4A;letter-spacing:0.08em">
            <span>← More Aggressive</span><span>More Defensive →</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="sh" style="margin-top:36px">Current ETF Allocation</div>',
                    unsafe_allow_html=True)
        wt_p = root / "data" / "config" / "portfolio_weights.xlsx" if True else None
        root = Path(__file__).resolve().parent
        wt_p = root / "data" / "config" / "portfolio_weights.xlsx"
        if wt_p.exists():
            wdf = pd.read_excel(wt_p).dropna(subset=["ETF Ticker"])
            wdf = wdf[wdf["ETF Ticker"].astype(str).str.strip() != "TOTAL"]
            wdf = wdf.sort_values("Portfolio Weight (%)", ascending=False)
            max_w = wdf["Portfolio Weight (%)"].max()
            rows = ""
            for _, r in wdf.iterrows():
                w   = float(r["Portfolio Weight (%)"])
                pct = min(w/max_w*100, 100)
                rows += (f'<tr>'
                         f'<td class="tk" style="width:60px">{r["ETF Ticker"]}</td>'
                         f'<td class="nm">{r.get("ETF Name","")}</td>'
                         f'<td class="bar-cell" style="width:38%">'
                         f'<div class="bar-bg"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
                         f'</td>'
                         f'<td class="wt">{w:.1f}%</td>'
                         f'</tr>')
            st.markdown(
                f'<table class="at" style="font-size:11px"><thead><tr>'
                f'<th>Ticker</th><th>ETF Name</th><th></th><th class="r">Weight</th>'
                f'</tr></thead><tbody>{rows}</tbody></table>',
                unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════
    # TAB 5 — Documents
    # ════════════════════════════════════════════════════════
    with tabs[4]:
        st.markdown('<div class="sh">Fund Documents</div>', unsafe_allow_html=True)
        if d.get("pdf_bytes"):
            col1, col2 = st.columns([2,3])
            with col1:
                st.markdown(f"""
                <div style="border:1px solid rgba(139,26,26,0.15);padding:20px 22px;background:#FFFFFF;margin-bottom:12px">
                    <div style="font-size:9px;color:#8B6A4A;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px">Monthly Factsheet</div>
                    <div style="font-size:13px;font-weight:600;color:#2C1810;margin-bottom:4px">{name}</div>
                    <div style="font-size:11px;color:#8B6A4A;margin-bottom:16px">{month}  ·  4 pages</div>
                """, unsafe_allow_html=True)
                st.download_button(
                    "Download PDF",
                    data=d["pdf_bytes"],
                    file_name=d["pdf_name"],
                    mime="application/pdf",
                )
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("PDF not yet generated. Run `python -m src.generate_report`.")

        st.markdown("""
        <div style="margin-top:32px;font-size:10px;color:#8B6A4A;line-height:1.8;
             border-top:1px solid rgba(139,26,26,0.12);padding-top:16px">
            <strong style="color:#2C1810">Disclaimer</strong><br>
            This dashboard is prepared for informational purposes only and does not constitute
            investment advice, a solicitation, or an offer to buy or sell any security.
            Past performance is not indicative of future results. Investments are subject to
            market risks including the possible loss of principal. Right Horizons Wealth Management.
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()