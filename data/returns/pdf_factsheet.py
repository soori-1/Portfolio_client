"""
RH Momentum Global ETF Portfolio — 4-page PDF factsheet generator.
Matches the May 2026 template exactly using ReportLab canvas.

Page 1: Portfolio Framework + Allocation Strategy
Page 2: YTD Cumulative Return chart + Market Exposure donuts
Page 3: Monthly Performance bar chart + table + Best/Worst performers
Page 4: Country/Sector exposure tables + Portfolio Highlights + Disclaimer
"""
from __future__ import annotations

from pathlib import Path
from datetime import date
import math

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# ── Brand colours ───────────────────────────────────────────────────────────
MAROON   = HexColor("#8B1A1A")
GOLD     = HexColor("#C9A84C")
CREAM    = HexColor("#F5ECD7")
DARK     = HexColor("#2E2E2E")
GREY     = HexColor("#6B6B6B")
LGREY    = HexColor("#E8E0D0")
WHITE    = white

W, H = A4  # 595.28 x 841.89 pts

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.png"


# ── Public entry point ───────────────────────────────────────────────────────

def generate_factsheet(
    output_path: Path,
    performance: dict,
    lookthrough_sheets: dict,
    report_month: str,          # e.g. "May 2026"
    reference_date: str,        # e.g. "06 May 2026"
    n_holdings: int,
    portfolio_name: str,
    benchmark_name: str,
    company_name: str,
    tagline: str,
    commentary_path: Path,
    disclaimer_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = rl_canvas.Canvas(str(output_path), pagesize=A4)

    disclaimer = disclaimer_path.read_text() if disclaimer_path.exists() else ""
    commentary = _load_commentary(commentary_path)

    _page1(c, report_month, reference_date, n_holdings,
           portfolio_name, company_name, tagline, disclaimer)
    _page2(c, performance, report_month,
           portfolio_name, company_name, tagline, disclaimer)
    _page3(c, performance, report_month,
           portfolio_name, company_name, tagline, disclaimer)
    _page4(c, lookthrough_sheets, commentary, report_month,
           portfolio_name, company_name, tagline, disclaimer)

    c.save()


# ── Shared helpers ───────────────────────────────────────────────────────────

def _header(c, portfolio_name, company_name, tagline, report_month, page_num, total_pages=4):
    """Draw the standard page header with logo, title bar and page number."""
    # Logo
    if LOGO_PATH.exists():
        c.drawImage(str(LOGO_PATH), 15*mm, H - 18*mm, width=35*mm, height=12*mm,
                    preserveAspectRatio=True, mask='auto')

    # Top title strip
    c.setFillColor(LGREY)
    c.rect(55*mm, H - 18*mm, W - 70*mm, 10*mm, fill=1, stroke=0)
    c.setFillColor(GREY)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(W/2, H - 13*mm,
        f"{portfolio_name.upper()}  ·  Fact sheet — {report_month}")

    # Footer
    c.setFillColor(MAROON)
    c.rect(0, 0, W, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica", 6.5)
    c.drawString(15*mm, 3*mm, f"{company_name}  ·  {tagline}")
    c.drawRightString(W - 15*mm, 3*mm, f"Page {page_num} of {total_pages}")

    # Maroon separator line under header
    c.setStrokeColor(MAROON)
    c.setLineWidth(0.8)
    c.line(15*mm, H - 20*mm, W - 15*mm, H - 20*mm)


def _section_title(c, text, x, y):
    c.setFillColor(MAROON)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, text)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.line(x, y - 1.5*mm, x + len(text) * 5.5, y - 1.5*mm)


def _load_commentary(path: Path) -> list[str]:
    if not path.exists():
        return ["Portfolio performed in line with expectations."]
    text = path.read_text()
    bullets = []
    for line in text.splitlines():
        line = line.strip().lstrip("-◆•*").strip()
        if line and not line.startswith("#"):
            bullets.append(line)
    return bullets[:6]


def _fig_to_image(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor="none", transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _draw_image_bytes(c, img_bytes: bytes, x, y, w, h):
    from reportlab.lib.utils import ImageReader
    buf = io.BytesIO(img_bytes)
    img = ImageReader(buf)
    c.drawImage(img, x, y, width=w, height=h,
                preserveAspectRatio=True, mask='auto')


# ── Page 1: Framework + Allocation Strategy ──────────────────────────────────

def _page1(c, report_month, reference_date, n_holdings,
           portfolio_name, company_name, tagline, disclaimer):
    _header(c, portfolio_name, company_name, tagline, report_month, 1)

    # Main title
    c.setFillColor(MAROON)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(15*mm, H - 35*mm, portfolio_name.upper())
    c.setFont("Helvetica", 11)
    c.setFillColor(GOLD)
    c.drawString(15*mm, H - 43*mm, f"Monthly Report  ·  {report_month}")
    c.setFillColor(GREY)
    c.setFont("Helvetica", 8.5)
    c.drawString(15*mm, H - 49*mm,
        f"Reference Date: {reference_date}   |   {n_holdings} Holdings")

    # Separator
    c.setStrokeColor(MAROON)
    c.setLineWidth(0.5)
    c.line(15*mm, H - 52*mm, W - 15*mm, H - 52*mm)

    # ── Portfolio Framework section ──
    _section_title(c, "Portfolio Framework", 15*mm, H - 60*mm)

    # Framework title (centred)
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, H - 70*mm, "Portfolio Framework")

    # Three framework boxes
    box_w = 54*mm
    box_h = 72*mm
    gap   = 6*mm
    total_w = 3 * box_w + 2 * gap
    start_x = (W - total_w) / 2
    box_y   = H - 148*mm

    box_data = [
        ("CORE\n30 – 50%",    "Consistency & Risk\nControl",
         "Focus towards diverse global equity. High-quality fixed income\nand low-volatility strategies.\nStability anchor.",
         "Stability Anchor"),
        ("MOMENTUM\n30 – 50%", "Tactical Alpha &\nCycle Capture",
         "Trend-following, sector rotation,\nfactor tilts. Actively rebalanced\nwith macro regime signals.",
         "Alpha Engine"),
        ("AGGRESSIVE\n0 – 30%", "High-Conviction\nOutperformance",
         "Concentrated high-upside\npositions. Growth equities,\nsatellite alternatives,\nspecial situations.",
         "Return Booster"),
    ]

    for i, (title, subtitle, body, tag) in enumerate(box_data):
        bx = start_x + i * (box_w + gap)

        # Box border
        c.setStrokeColor(GOLD)
        c.setFillColor(WHITE)
        c.setLineWidth(1.2)
        c.roundRect(bx, box_y, box_w, box_h, 3*mm, fill=1, stroke=1)

        # Title
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        lines = title.split("\n")
        c.drawCentredString(bx + box_w/2, box_y + box_h - 8*mm, lines[0])
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(MAROON)
        c.drawCentredString(bx + box_w/2, box_y + box_h - 14*mm, lines[1])

        # Subtitle
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        for j, sl in enumerate(subtitle.split("\n")):
            c.drawCentredString(bx + box_w/2,
                                box_y + box_h - 22*mm - j*4*mm, sl)

        # Body
        c.setFont("Helvetica", 7)
        c.setFillColor(GREY)
        body_y = box_y + box_h - 34*mm
        for line in body.split("\n"):
            c.drawCentredString(bx + box_w/2, body_y, line)
            body_y -= 3.8*mm

        # Tag pill
        pill_w = 32*mm
        pill_h = 6*mm
        pill_x = bx + (box_w - pill_w) / 2
        pill_y = box_y + 4*mm
        c.setStrokeColor(GOLD)
        c.setFillColor(WHITE)
        c.setLineWidth(0.8)
        c.roundRect(pill_x, pill_y, pill_w, pill_h, 2*mm, fill=1, stroke=1)
        c.setFillColor(GOLD)
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx + box_w/2, pill_y + 1.8*mm, tag)

    # ── Allocation Strategy section ──
    _section_title(c, "Allocation Strategy", 15*mm, H - 162*mm)
    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(15*mm, H - 168*mm,
        "Dynamic allocation across market cycles — Early Expansion through Contraction")

    # Strategy title
    c.setFillColor(DARK)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, H - 178*mm, "Allocation Strategy")

    # Timeline arrow
    arrow_y  = H - 196*mm
    arrow_x1 = 20*mm
    arrow_x2 = W - 20*mm
    c.setStrokeColor(MAROON)
    c.setLineWidth(1.5)
    c.line(arrow_x1, arrow_y, arrow_x2, arrow_y)
    # Arrowhead
    c.setFillColor(MAROON)
    c.beginPath()
    p = c.beginPath(); p.moveTo(arrow_x2, arrow_y)
    p.lineTo(arrow_x2 - 3*mm, arrow_y + 1.5*mm)
    p.lineTo(arrow_x2 - 3*mm, arrow_y - 1.5*mm)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Phases
    phases = [
        ("EARLY\nEXPANSION",  arrow_x1 + 10*mm),
        ("MID\nCYCLE",         arrow_x1 + 55*mm),
        ("LATE\nCYCLE",        arrow_x1 + 105*mm),
        ("CONTRACTION",        arrow_x1 + 148*mm),
    ]
    for label, px in phases:
        c.setFillColor(MAROON)
        c.circle(px, arrow_y, 2*mm, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 7.5)
        for k, ln in enumerate(label.split("\n")):
            c.drawCentredString(px, arrow_y + 6*mm + k * (-4*mm), ln)

    # Strategy boxes below arrow
    strat_data = [
        ("Momentum\n+ Aggressive",  phases[0][1]),
        ("Balanced",                phases[1][1]),
        ("Core +\nMomentum",        phases[2][1]),
        ("Increase Core\n+\nIncrease Cash", phases[3][1]),
    ]
    box_y2 = arrow_y - 28*mm
    for label, cx in strat_data:
        bw2 = 38*mm
        bh2 = 22*mm
        c.setStrokeColor(GOLD)
        c.setFillColor(WHITE)
        c.setLineWidth(1)
        c.roundRect(cx - bw2/2, box_y2, bw2, bh2, 2*mm, fill=1, stroke=1)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        lines2 = label.split("\n")
        total_h2 = len(lines2) * 4*mm
        start_y2 = box_y2 + bh2/2 + total_h2/2 - 3*mm
        for ln in lines2:
            c.drawCentredString(cx, start_y2, ln)
            start_y2 -= 4*mm

    c.showPage()


# ── Page 2: YTD chart + Market Exposure donuts ───────────────────────────────

def _page2(c, performance, report_month,
           portfolio_name, company_name, tagline, disclaimer):
    _header(c, portfolio_name, company_name, tagline, report_month, 2)

    _section_title(c, "Portfolio Profitability — Cumulative YTD Return", 15*mm, H - 30*mm)

    table   = performance["monthly_table"]
    monthly = table[table["Month"] != "YTD"].copy()

    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 8)
    first_month = monthly["Month Label"].iloc[0] if len(monthly) else ""
    last_month  = monthly["Month Label"].iloc[-1] if len(monthly) else ""
    c.drawString(15*mm, H - 37*mm,
        f"{portfolio_name} vs. MSCI All Country World Index (ACWI) Benchmark  ·  "
        f"{first_month} – {last_month}")

    # YTD line chart
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    fig.patch.set_alpha(0)
    ax.set_facecolor("#F0F7FF")

    months_short = [m.split()[0][:3] for m in monthly["Month Label"]]
    port_cum  = monthly["Cum_Portfolio (%)"].tolist()
    bench_cum = monthly["Cum_Benchmark (%)"].tolist()

    # Prepend zero
    x_vals = list(range(len(months_short) + 1))
    port_line  = [0] + port_cum
    bench_line = [0] + bench_cum

    ax.fill_between(x_vals, port_line, bench_line,
                    where=[p >= b for p, b in zip(port_line, bench_line)],
                    alpha=0.15, color="#1a6bb5")
    ax.plot(x_vals, port_line,  color="#1a6bb5", linewidth=2.5, label="Portfolio")
    ax.plot(x_vals, bench_line, color="#8B5A00", linewidth=2.5, label="ACWI")

    # End labels
    ax.annotate(f"{port_cum[-1]:.2f}%",
                xy=(x_vals[-1], port_line[-1]),
                xytext=(8, 0), textcoords="offset points",
                color="#1a6bb5", fontweight="bold", fontsize=9, va="center")
    ax.annotate(f"{bench_cum[-1]:.2f}%",
                xy=(x_vals[-1], bench_line[-1]),
                xytext=(8, 0), textcoords="offset points",
                color="#8B5A00", fontweight="bold", fontsize=9, va="center")

    ax.set_xticks(x_vals[1:])
    ax.set_xticklabels(months_short, fontsize=8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.2f}%"))
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", color="#dddddd", linewidth=0.5)
    ax.spines[['top','right','bottom']].set_visible(False)

    # Legend
    ax.legend(["Portfolio", "ACWI"], loc="upper left", fontsize=8,
              framealpha=0, ncol=2)

    img_bytes = _fig_to_image(fig)
    _draw_image_bytes(c, img_bytes, 15*mm, H - 120*mm, W - 30*mm, 75*mm)

    # ── Market Exposure section ──
    _section_title(c, "Market Exposure", 15*mm, H - 127*mm)
    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(15*mm, H - 133*mm,
        f"Portfolio allocation across market classifications as of {report_month}")

    me = performance["market_exposure"]
    _draw_donut(c, me["by_market"],
                cx=70*mm, cy=H - 185*mm, r=28*mm,
                title="Exposure",
                colors_list=["#2E86C1", "#27AE60", "#D4AC0D"],
                label_x=115*mm, label_y=H - 168*mm)

    _draw_donut(c, me["by_type"],
                cx=W/2 + 40*mm, cy=H - 185*mm, r=28*mm,
                title="ETF Type",
                colors_list=["#27AE60", "#D4AC0D", "#AAB7B8"],
                label_x=W/2 + 80*mm, label_y=H - 168*mm)

    c.showPage()


def _draw_donut(c, data: dict, cx, cy, r, title, colors_list, label_x, label_y):
    fig, ax = plt.subplots(figsize=(2.8, 2.8))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    vals   = list(data.values())
    labels = list(data.keys())
    used_colors = colors_list[:len(vals)]

    wedges, _ = ax.pie(vals, colors=used_colors,
                       startangle=90, counterclock=False,
                       wedgeprops={"width": 0.55, "edgecolor": "white", "linewidth": 1.5})
    ax.text(0, 0, title, ha="center", va="center",
            fontsize=8.5, fontweight="bold", color="#2E2E2E")
    ax.axis("equal")

    img_bytes = _fig_to_image(fig)
    _draw_image_bytes(c, img_bytes, cx - r, cy - r, r*2, r*2)

    # Legend to the right
    c.setFont("Helvetica", 8)
    ly = label_y
    for i, (label, val) in enumerate(data.items()):
        col = HexColor(used_colors[i % len(used_colors)])
        c.setFillColor(col)
        c.rect(label_x, ly - 2*mm, 4*mm, 4*mm, fill=1, stroke=0)
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(label_x + 5.5*mm, ly - 0.5*mm, label)
        c.setFont("Helvetica", 8)
        c.setFillColor(GOLD)
        c.drawString(label_x + 5.5*mm, ly - 4.5*mm, f"{val:.1f}%")
        ly -= 11*mm


# ── Page 3: Bar chart + Table + Best/Worst ───────────────────────────────────

def _page3(c, performance, report_month,
           portfolio_name, company_name, tagline, disclaimer):
    _header(c, portfolio_name, company_name, tagline, report_month, 3)

    table   = performance["monthly_table"]
    monthly = table[table["Month"] != "YTD"].copy()
    ytd_row = table[table["Month"] == "YTD"].iloc[0]

    _section_title(c, "Monthly Performance vs. Benchmark", 15*mm, H - 30*mm)
    c.setFillColor(GREY)
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(15*mm, H - 36*mm,
        f"Monthly returns: Portfolio % vs. ACWI %  ·  "
        f"{monthly['Month Label'].iloc[0].split()[0]} – "
        f"{monthly['Month Label'].iloc[-1].split()[0]} "
        f"{monthly['Month Label'].iloc[-1].split()[-1]}")

    # Bar chart
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    months_short = [m.split()[0][:3] for m in monthly["Month Label"]]
    n = len(months_short)
    x = range(n)
    w = 0.38

    bars_p = ax.bar([i - w/2 for i in x], monthly["Portfolio (%)"],
                    width=w, color="#1a6bb5", label="Portfolio %")
    bars_b = ax.bar([i + w/2 for i in x], monthly["Benchmark (%)"],
                    width=w, color="#8B5A00", label="ACWI %")

    # Value labels on bars
    for bar in list(bars_p) + list(bars_b):
        h = bar.get_height()
        sign = "+" if h >= 0 else ""
        ax.annotate(f"{sign}{h:.2f}%",
                    xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 2 if h >= 0 else -8),
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=6.5, fontweight="bold",
                    color=bar.get_facecolor())

    ax.set_xticks(list(x))
    ax.set_xticklabels(months_short, fontsize=8)
    ax.axhline(0, color="#aaaaaa", linewidth=0.8)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", color="#eeeeee", linewidth=0.5)
    ax.spines[['top','right','bottom']].set_visible(False)
    ax.legend(fontsize=8, framealpha=0, ncol=2, loc="upper right")

    img_bytes = _fig_to_image(fig)
    _draw_image_bytes(c, img_bytes, 15*mm, H - 110*mm, W - 30*mm, 68*mm)

    # ── Performance table ──
    _section_title(c, "Monthly Performance vs. Benchmark", 15*mm, H - 117*mm)

    def sign(v):
        return f"+{v:.2f}%" if v >= 0 else f"{v:.2f}%"

    tdata = [["Month", "Portfolio %", "ACWI %", "Outperformance"]]
    for _, row in monthly.iterrows():
        tdata.append([
            row["Month Label"],
            sign(row["Portfolio (%)"]),
            sign(row["Benchmark (%)"]),
            sign(row["Outperformance (%)"]),
        ])
    # YTD row
    tdata.append([
        "YTD Cumulative",
        sign(ytd_row["Portfolio (%)"]),
        sign(ytd_row["Benchmark (%)"]),
        sign(ytd_row["Outperformance (%)"]),
    ])

    col_widths = [45*mm, 38*mm, 32*mm, 42*mm]
    t = Table(tdata, colWidths=col_widths, rowHeights=7*mm)
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0),  HexColor("#8B1A1A")),
        ("TEXTCOLOR",   (0,0), (-1,0),  colors.white),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [HexColor("#FFFFFF"), HexColor("#FAF3E8")]),
        ("BACKGROUND",  (0,-1), (-1,-1), HexColor("#F5ECD7")),
        ("FONTNAME",    (0,-1), (-1,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (1,1), (1,-1),  HexColor("#1a6bb5")),
        ("TEXTCOLOR",   (2,1), (2,-1),  HexColor("#8B5A00")),
        ("TEXTCOLOR",   (3,1), (3,-1),  HexColor("#27AE60")),
        ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#E8E0D0")),
        ("TOPPADDING",  (0,0), (-1,-1), 1),
        ("BOTTOMPADDING",(0,0),(-1,-1), 1),
    ]))

    table_h = (len(tdata)) * 7*mm
    t.wrapOn(c, W - 30*mm, table_h)
    t.drawOn(c, 15*mm, H - 117*mm - table_h - 3*mm)

    table_bottom = H - 117*mm - table_h - 10*mm

    # ── Best & Worst ──
    bw = performance["best_worst"]
    _section_title(c, f"Best & Worst Performers — {report_month}", 15*mm, table_bottom)

    col_w = (W - 30*mm) / 2 - 3*mm
    gainer_x  = 15*mm
    laggard_x = 15*mm + col_w + 6*mm
    bw_y      = table_bottom - 10*mm

    # Headers
    for hx, htxt, hcol in [
        (gainer_x,  "TOP GAINERS",  "#8B1A1A"),
        (laggard_x, "LAGGARDS",     "#8B1A1A"),
    ]:
        c.setFillColor(HexColor(hcol))
        c.rect(hx, bw_y - 6*mm, col_w, 6*mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(hx + col_w/2, bw_y - 3.5*mm, htxt)

    # Rows
    row_h = 9*mm
    for idx, entry in enumerate(bw.get("gainers", [])):
        ry = bw_y - 6*mm - (idx+1)*row_h
        fill = HexColor("#FFFFFF") if idx % 2 == 0 else HexColor("#FAF3E8")
        c.setFillColor(fill)
        c.rect(gainer_x, ry, col_w, row_h, fill=1, stroke=0)
        c.setFillColor(MAROON)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(gainer_x + 2*mm, ry + 3*mm, entry["ticker"])
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7.5)
        name = entry["name"][:34]
        c.drawString(gainer_x + 14*mm, ry + 3*mm, name)
        c.setFillColor(HexColor("#27AE60"))
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(gainer_x + col_w - 2*mm, ry + 3*mm,
                          f"(+{entry['return']:.2f}%)")

    for idx, entry in enumerate(bw.get("laggards", [])):
        ry = bw_y - 6*mm - (idx+1)*row_h
        fill = HexColor("#FFFFFF") if idx % 2 == 0 else HexColor("#FAF3E8")
        c.setFillColor(fill)
        c.rect(laggard_x, ry, col_w, row_h, fill=1, stroke=0)
        c.setFillColor(MAROON)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(laggard_x + 2*mm, ry + 3*mm, entry["ticker"])
        c.setFillColor(DARK)
        c.setFont("Helvetica", 7.5)
        name = entry["name"][:34]
        c.drawString(laggard_x + 14*mm, ry + 3*mm, name)
        ret = entry["return"]
        ret_str = f"(+{ret:.2f}%)" if ret >= 0 else f"({ret:.2f}%)"
        col_ret = HexColor("#C0392B") if ret < 0 else HexColor("#27AE60")
        c.setFillColor(col_ret)
        c.setFont("Helvetica-Bold", 8)
        c.drawRightString(laggard_x + col_w - 2*mm, ry + 3*mm, ret_str)

    c.showPage()


# ── Page 4: Country/Sector + Commentary + Disclaimer ─────────────────────────

def _page4(c, lookthrough_sheets, commentary, report_month,
           portfolio_name, company_name, tagline, disclaimer):
    _header(c, portfolio_name, company_name, tagline, report_month, 4)

    country_df = lookthrough_sheets["Country Exposure"]
    sector_df  = lookthrough_sheets["Sector Exposure"]

    # Filter out Global/Unknown/Diversified for cleaner display
    country_clean = country_df[~country_df["Country"].isin(
        ["Global", "Unknown", "Diversified", "Unclassified"]
    )].head(8)
    sector_clean  = sector_df[~sector_df["Sector"].isin(
        ["Unclassified", "Diversified", "Commodities"]
    )].head(8)

    top_w = country_clean["Portfolio Weight (%)"].max() if len(country_clean) else 1

    # ── Country table ──
    y_start = H - 30*mm
    _section_title(c, "Top Countries — Exposure Breakdown", 15*mm, y_start)

    _draw_exposure_table(c, country_clean, "Country", 15*mm, y_start - 8*mm,
                         W - 30*mm, top_w)

    # ── Sector table ──
    sec_y = y_start - 8*mm - len(country_clean) * 9*mm - 12*mm
    _section_title(c, "Top Sectors — Exposure Breakdown", 15*mm, sec_y)

    top_w_sec = sector_clean["Portfolio Weight (%)"].max() if len(sector_clean) else 1
    _draw_exposure_table(c, sector_clean, "Sector", 15*mm, sec_y - 8*mm,
                         W - 30*mm, top_w_sec)

    # ── Commentary ──
    comm_y = sec_y - 8*mm - len(sector_clean) * 9*mm - 12*mm
    _section_title(c, f"Portfolio Highlights — {report_month}", 15*mm, comm_y)

    box_h  = min(len(commentary) * 11*mm + 8*mm, 60*mm)
    box_y  = comm_y - 8*mm - box_h
    c.setStrokeColor(GOLD)
    c.setFillColor(HexColor("#FFFDF5"))
    c.setLineWidth(0.8)
    c.roundRect(15*mm, box_y, W - 30*mm, box_h, 2*mm, fill=1, stroke=1)

    c.setFillColor(MAROON)
    bullet_y = comm_y - 12*mm
    for bullet in commentary:
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(19*mm, bullet_y, "◆")
        c.setFillColor(DARK)
        c.setFont("Helvetica", 8)
        # Word wrap
        words    = bullet.split()
        line     = ""
        line_x   = 25*mm
        max_w_pts = W - 40*mm
        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, "Helvetica", 8) < max_w_pts:
                line = test
            else:
                c.drawString(line_x, bullet_y, line)
                bullet_y -= 4*mm
                line = word
        if line:
            c.drawString(line_x, bullet_y, line)
        bullet_y -= 7*mm

    # ── Disclaimer ──
    if disclaimer:
        disc_y = box_y - 8*mm
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(15*mm, disc_y, "DISCLAIMER")
        c.setFont("Helvetica-Oblique", 6)
        c.setFillColor(GREY)
        disc_y -= 4*mm
        words = disclaimer.split()
        line  = ""
        for word in words:
            test = line + (" " if line else "") + word
            if c.stringWidth(test, "Helvetica-Oblique", 6) < (W - 30*mm):
                line = test
            else:
                c.drawString(15*mm, disc_y, line)
                disc_y -= 3.5*mm
                line = word
                if disc_y < 12*mm:
                    break
        if line and disc_y > 12*mm:
            c.drawString(15*mm, disc_y, line)

    c.showPage()


def _draw_exposure_table(c, df, name_col, x, y, width, max_weight):
    bar_col_w = width * 0.55
    wt_col_w  = width * 0.18
    nm_col_w  = width - bar_col_w - wt_col_w
    row_h     = 9*mm

    # Header
    c.setFillColor(MAROON)
    c.rect(x, y - 6*mm, width, 6*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 2*mm, y - 4*mm, name_col)
    c.drawCentredString(x + nm_col_w + bar_col_w/2, y - 4*mm, "Allocation Visual")
    c.drawCentredString(x + nm_col_w + bar_col_w + wt_col_w/2, y - 4*mm, "Weight")

    for idx, (_, row) in enumerate(df.iterrows()):
        ry   = y - 6*mm - (idx+1)*row_h
        fill = HexColor("#FFFFFF") if idx % 2 == 0 else HexColor("#FAF3E8")
        c.setFillColor(fill)
        c.rect(x, ry, width, row_h, fill=1, stroke=0)

        # Name
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold" if idx == 0 else "Helvetica", 8)
        c.drawString(x + 2*mm, ry + 3*mm, str(row[name_col])[:28])

        # Bar
        weight = float(row["Portfolio Weight (%)"])
        bar_pct = weight / max_weight if max_weight > 0 else 0
        bar_filled_w = bar_col_w * 0.85 * bar_pct
        bar_empty_w  = bar_col_w * 0.85 - bar_filled_w
        bar_x = x + nm_col_w
        bar_y = ry + 3*mm

        c.setFillColor(MAROON)
        c.rect(bar_x, bar_y, bar_filled_w, 3*mm, fill=1, stroke=0)
        c.setFillColor(HexColor("#E8E0D0"))
        c.rect(bar_x + bar_filled_w, bar_y, bar_empty_w, 3*mm, fill=1, stroke=0)

        # Weight label
        c.setFillColor(DARK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(
            x + nm_col_w + bar_col_w + wt_col_w/2,
            ry + 3*mm,
            f"{weight:.1f}%"
        )
