"""
Sector and country normalizer.

Maps issuer-provided sector/country strings to canonical GICS (11 sectors).
Falls back to keyword matching on security name when sector is missing.
"""
from __future__ import annotations
import re
import pandas as pd

# ---------------------------------------------------------------------------
# Canonical GICS sectors (11)
# ---------------------------------------------------------------------------
GICS_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
    "Commodities",   # Non-GICS bucket for gold/commodity ETFs
    "Unclassified",
]

# ---------------------------------------------------------------------------
# Issuer sector string → GICS mapping
# Covers iShares, Global X, Vanguard label variants
# ---------------------------------------------------------------------------
SECTOR_MAP: dict[str, str] = {
    # Information Technology
    "information technology":       "Information Technology",
    "technology":                   "Information Technology",
    "tech":                         "Information Technology",
    "software & services":          "Information Technology",
    "semiconductors":               "Information Technology",
    "semiconductor":                "Information Technology",
    "hardware":                     "Information Technology",
    "electronic equipment":         "Information Technology",
    "it":                           "Information Technology",
    "technologie informacyjne":     "Information Technology",
    # Communication Services
    "communication services":       "Communication Services",
    "communication":                "Communication Services",
    "telecommunications":           "Communication Services",
    "telecom":                      "Communication Services",
    "media":                        "Communication Services",
    "interactive media":            "Communication Services",
    "diversified telecommunication services": "Communication Services",
    "wireless telecommunication services":    "Communication Services",
    # Consumer Discretionary
    "consumer discretionary":       "Consumer Discretionary",
    "consumer cyclical":            "Consumer Discretionary",
    "consumer cyclicals":           "Consumer Discretionary",
    "cyclical consumer goods":      "Consumer Discretionary",
    "retailing":                    "Consumer Discretionary",
    "automobiles":                  "Consumer Discretionary",
    "hotels restaurants leisure":   "Consumer Discretionary",
    # Consumer Staples
    "consumer staples":             "Consumer Staples",
    "consumer defensive":           "Consumer Staples",
    "non-cyclical consumer goods":  "Consumer Staples",
    "food beverage tobacco":        "Consumer Staples",
    "food & staples retailing":     "Consumer Staples",
    # Energy
    "energy":                       "Energy",
    "oil gas consumable fuels":     "Energy",
    "oil & gas":                    "Energy",
    # Financials
    "financials":                   "Financials",
    "financial services":           "Financials",
    "finance":                      "Financials",
    "banks":                        "Financials",
    "insurance":                    "Financials",
    "diversified financials":       "Financials",
    "capital markets":              "Financials",
    # Health Care
    "health care":                  "Health Care",
    "healthcare":                   "Health Care",
    "health":                       "Health Care",
    "pharmaceuticals":              "Health Care",
    "biotechnology":                "Health Care",
    "medical devices":              "Health Care",
    "life sciences tools":          "Health Care",
    # Industrials
    "industrials":                  "Industrials",
    "industrial":                   "Industrials",
    "capital goods":                "Industrials",
    "transportation":               "Industrials",
    "commercial professional services": "Industrials",
    # Materials
    "materials":                    "Materials",
    "basic materials":              "Materials",
    "chemicals":                    "Materials",
    "metals mining":                "Materials",
    "metals & mining":              "Materials",
    # Real Estate
    "real estate":                  "Real Estate",
    "reits":                        "Real Estate",
    "reit":                         "Real Estate",
    # Utilities
    "utilities":                    "Utilities",
    "utility":                      "Utilities",
    # Commodities
    "commodities":                  "Commodities",
    "commodity":                    "Commodities",
    "precious metals":              "Commodities",
    "gold":                         "Commodities",
    "diversified":                  "Unclassified",
    "cash":                         "Unclassified",
    "cash and/or derivatives":      "Unclassified",
    "money market":                 "Unclassified",
}

# ---------------------------------------------------------------------------
# Name-based keyword → GICS fallback
# Applied when sector field is blank/unknown
# ---------------------------------------------------------------------------
NAME_KEYWORDS: list[tuple[str, str]] = [
    # IT
    (r"semiconductor|chip|wafer|foundry|fabless|tsmc|nvidia|intel|amd|qualcomm|broadcom|micron|asml|lam research|applied materials|kla|synopsys|cadence|analog devices|texas instruments|marvell|arm hold",
     "Information Technology"),
    (r"software|cloud|saas|microsoft|oracle|sap|salesforce|servicenow|workday|adobe|intuit|autodesk|palantir|snowflake|datadog|mongodb|elastic|crowdstrike|palo alto|fortinet|cyber|security",
     "Information Technology"),
    (r"apple|alphabet|google|meta|facebook|amazon web|aws|alibaba cloud",
     "Information Technology"),
    # Communication Services
    (r"telecom|wireless|mobile|verizon|at&t|t-mobile|comcast|charter|netflix|disney|warner|paramount|spotify|tencent|bytedance|baidu|naver|kakao",
     "Communication Services"),
    # Consumer Discretionary
    (r"amazon|tesla|nike|lvmh|hermes|luxury|hotel|restaurant|airbnb|booking|expedia|carnival|mcdonald|starbucks|toyota|volkswagen|bmw|mercedes|ford|general motors|honda|hyundai|kia|stellantis|shopify",
     "Consumer Discretionary"),
    # Consumer Staples
    (r"nestle|unilever|procter|p&g|coca.cola|pepsi|colgate|walmart|costco|kroger|target|l'oreal|diageo|heineken|anheuser|philip morris|altria|british american tobacco",
     "Consumer Staples"),
    # Energy
    (r"oil|gas|petroleum|exxon|chevron|shell|bp |total energie|conocophillips|pioneer|schlumberger|halliburton|baker hughes|valero|marathon|enbridge|energy transfer|hydrogen|hydr",
     "Energy"),
    # Financials
    (r"bank|financial|insurance|jpmorgan|goldman|morgan stanley|citigroup|hsbc|barclays|ubs|credit suisse|bnp|societe generale|blackrock|vanguard|berkshire|visa|mastercard|american express|paypal|fiserv|blackstone|kkr|carlyle|apollo",
     "Financials"),
    # Health Care
    (r"pharma|biotech|medical|health|johnson|pfizer|roche|novartis|sanofi|astrazeneca|merck|abbvie|lilly|bristol|regeneron|moderna|biontech|unitedhealth|cvs|cigna|humana|medtronic|abbott|thermo fisher|danaher|intuitive surgical",
     "Health Care"),
    # Industrials
    (r"aerospace|defense|industrial|caterpillar|deere|honeywell|ge |general electric|siemens|schneider|emerson|rockwell|eaton|parker|illinois tool|3m|raytheon|lockheed|northrop|boeing|airbus|fedex|ups |union pacific|csx|norfolk|waste management|republic services",
     "Industrials"),
    # Materials
    (r"mining|steel|aluminum|copper|lithium|chemical|basf|dow |dupont|linde|air products|bhp|rio tinto|vale|freeport|newmont|barrick|anglogold|lynas|livent|albemarle|lit ",
     "Materials"),
    # Real Estate
    (r"reit|real estate|property|prologis|equinix|american tower|crown castle|digital realty|simon property|public storage|welltower|ventas|dtcr",
     "Real Estate"),
    # Utilities
    (r"electric|utility|utilities|nextera|duke energy|southern company|dominion|american electric|xcel|eversource|sempra|water|renewable|solar|wind farm",
     "Utilities"),
    # Commodities
    (r"gold|silver|platinum|metal trust|commodity|physical gold|bullion",
     "Commodities"),
]


def normalize_sector(sector_raw: str | None, security_name: str = "") -> str:
    """Map raw sector string to canonical GICS sector."""
    if sector_raw is not None and not (isinstance(sector_raw, float) and __import__('math').isnan(sector_raw)) and str(sector_raw).strip() not in ("", "nan", "N/A", "-", "<NA>"):
        key = str(sector_raw).strip().lower()
        # Direct map
        if key in SECTOR_MAP:
            return SECTOR_MAP[key]
        # Partial match
        for k, v in SECTOR_MAP.items():
            if k in key:
                return v

    # Fall back to name-based keyword matching
    if security_name:
        name_lower = str(security_name).lower()
        for pattern, sector in NAME_KEYWORDS:
            if re.search(pattern, name_lower):
                return sector

    return "Unclassified"


# ---------------------------------------------------------------------------
# Country normalizer
# ---------------------------------------------------------------------------
COUNTRY_MAP: dict[str, str] = {
    "united states": "United States", "us": "United States", "usa": "United States", "u.s.": "United States",
    "united kingdom": "United Kingdom", "uk": "United Kingdom", "gb": "United Kingdom", "great britain": "United Kingdom",
    "china": "China", "cn": "China", "hong kong": "Hong Kong", "hk": "Hong Kong",
    "taiwan": "Taiwan", "tw": "Taiwan",
    "japan": "Japan", "jp": "Japan",
    "south korea": "South Korea", "korea": "South Korea", "kr": "South Korea",
    "india": "India", "in": "India",
    "germany": "Germany", "de": "Germany",
    "france": "France", "fr": "France",
    "canada": "Canada", "ca": "Canada",
    "australia": "Australia", "au": "Australia",
    "brazil": "Brazil", "br": "Brazil",
    "switzerland": "Switzerland", "ch": "Switzerland",
    "netherlands": "Netherlands", "nl": "Netherlands",
    "sweden": "Sweden", "se": "Sweden",
    "denmark": "Denmark", "dk": "Denmark",
    "spain": "Spain", "es": "Spain",
    "italy": "Italy", "it": "Italy",
    "singapore": "Singapore", "sg": "Singapore",
    "poland": "Poland", "pl": "Poland",
    "ireland": "Ireland", "ie": "Ireland",
    "israel": "Israel", "il": "Israel",
    "mexico": "Mexico", "mx": "Mexico",
    "indonesia": "Indonesia", "id": "Indonesia",
    "saudi arabia": "Saudi Arabia", "sa": "Saudi Arabia",
    "south africa": "South Africa", "za": "South Africa",
    "russia": "Russia", "ru": "Russia",
    "global": "Global", "multi": "Global",
}


def normalize_country(country_raw: str | None) -> str:
    if country_raw is None or str(country_raw).strip() in ("", "nan", "N/A", "-", "<NA>"):
        return "Unknown"
    key = str(country_raw).strip().lower()
    return COUNTRY_MAP.get(key, str(country_raw).strip().title())