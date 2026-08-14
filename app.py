"""
DPS Scenario Tracker – Euro Stoxx 50 + selected extras
Features:
- Bear/Base/Bull with interim/final/quarterly breakdowns
- Morning newsflow scan + categorized alerts
- Yield Red-Flag (absolute + relative, banks less sensitive)
- Manual EPS Simulate + Reset to hard data
- Richer scenario rationales, historical policy, payout ranges
- DPS change flags
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date
import json
from pathlib import Path
from copy import deepcopy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_light(name, ticker, country, sector, currency, policy, payout_target,
               dps26, dps27, dps28, hist=None, fcf=1.5, nd=1.0, price=50.0,
               eps26=None, is_bank=False, notes=""):
    """Compact stock entry with usable placeholders."""
    hist = hist or {"FY23": round(dps26*0.85, 2), "FY24": round(dps26*0.92, 2), "FY25": round(dps26*0.97, 2)}
    eps26 = eps26 or (dps26 / max(payout_target, 0.25) if payout_target else dps26 * 2.5)
    return {
        "name": name, "country": country, "sector": sector, "fy_end": "12-31",
        "currency": currency, "policy": policy, "policy_flag": None,
        "shares_m": 1000.0, "last_reported": "–", "reported_eps_ytd": None,
        "eps": {"FY25a": round(eps26*0.92, 2), "FY26e": round(eps26, 2),
                "FY27e": round(eps26*1.08, 2), "FY28e": round(eps26*1.16, 2)},
        "dps_hist": hist,
        "consensus_dps": {"FY26e": dps26, "FY27e": dps27, "FY28e": dps28},
        "payout_target": payout_target, "fcf_cover": fcf, "net_debt_ebitda": nd,
        "price": price, "is_bank": is_bank,
        "scenarios": {
            "bear": {
                "FY26e": round(dps26*0.88, 3), "FY27e": round(dps27*0.85, 3), "FY28e": round(dps28*0.82, 3),
                "rationale": "Soft demand / higher costs / macro stress → slower growth, conservative payout",
                "eps_rationale": "Lower volumes or margins; possible one-offs. Macro (recession, rates, geopolitics) hits earnings.",
                "breakdown": {"Total": round(dps26*0.88, 3), "note": "Held or modest cut if cover tight"},
                "macro_sensitivity": "Vulnerable to recession / credit cycle / energy shock",
            },
            "base": {
                "FY26e": dps26, "FY27e": dps27, "FY28e": dps28,
                "rationale": "Consensus path; progressive or stable policy maintained",
                "eps_rationale": "In-line growth, normal margin trajectory, no major policy shift",
                "breakdown": {"Total": dps26, "note": "Standard pattern under current policy"},
                "macro_sensitivity": "Moderate; policy has some buffer",
            },
            "bull": {
                "FY26e": round(dps26*1.12, 3), "FY27e": round(dps27*1.15, 3), "FY28e": round(dps28*1.18, 3),
                "rationale": "Stronger FCF / higher payout or specials from excess capital",
                "eps_rationale": "Beat on volume/pricing/margins; possible guidance raise",
                "breakdown": {"Total": round(dps26*1.12, 3), "note": "Possible step-up or special"},
                "macro_sensitivity": "Benefits from soft-landing / stronger growth",
            },
        },
        "calendar_notes": notes or "See policy for payment lag vs fiscal year.",
        "risks": ["Macro", "Sector specific"],
        "upside_triggers": ["Guidance raise", "Higher payout"],
        "news_log": [],
        "transcript_insights": None,
        "historical_policy": f"Typical payout ~{int(payout_target*100)}%. Progressive or stable unless stressed.",
        "payout_range": f"{int(payout_target*80)}–{int(payout_target*120)}% of earnings (illustrative)",
    }

# ---------------------------------------------------------------------------
# Universe – rich names + light Euro Stoxx 50 core + extras
# ---------------------------------------------------------------------------
SAMPLE_UNIVERSE = {}

# === RICH (original enhanced) ===
SAMPLE_UNIVERSE["ASML.AS"] = {
    "name": "ASML Holding", "isin": "NL0010273215", "country": "NL", "sector": "Technology",
    "fy_end": "12-31", "currency": "EUR", "policy": "Multiple interims + final (progressive)",
    "policy_flag": None, "shares_m": 393.0, "last_reported": "Q2'26 (15 Jul)", "reported_eps_ytd": 7.4,
    "eps": {"FY25a": 24.73, "FY26e": 28.50, "FY27e": 33.00, "FY28e": 38.00},
    "dps_hist": {"FY23": 6.10, "FY24": 6.40, "FY25": 7.50},
    "consensus_dps": {"FY26e": 8.20, "FY27e": 9.60, "FY28e": 11.20},
    "payout_target": 0.30, "fcf_cover": 2.0, "net_debt_ebitda": -0.8, "price": 1550.0, "is_bank": False,
    "scenarios": {
        "bear": {
            "FY26e": 7.40, "FY27e": 8.20, "FY28e": 9.00,
            "rationale": "Soft orders / China export risk → slower growth, payout held",
            "eps_rationale": "Orders and sales below raised guidance; China restrictions bite. EPS growth slows to high-single digit.",
            "breakdown": {"Interims (3x)": 5.20, "Final": 2.20, "Total": 7.40, "note": "Lower interims if guidance cut"},
            "macro_sensitivity": "Semi cycle + geopolitics (China). Still strong FCF buffer.",
        },
        "base": {
            "FY26e": 8.20, "FY27e": 9.60, "FY28e": 11.20,
            "rationale": "Raised 2026 sales guidance (€43-45bn) + progressive interims",
            "eps_rationale": "Sales €43-45bn, GM 54-56%. AI/logic demand supports mid-teens EPS growth.",
            "breakdown": {"Interims (3x)": 5.64, "Final": 2.56, "Total": 8.20, "note": "Current interim ~€1.88"},
            "macro_sensitivity": "Resilient; net cash and high FCF cover give policy flexibility.",
        },
        "bull": {
            "FY26e": 9.00, "FY27e": 11.00, "FY28e": 13.50,
            "rationale": "AI demand continues + higher payout + specials from excess cash",
            "eps_rationale": "Further guidance raises; capacity expansion pays off. EPS accelerates.",
            "breakdown": {"Interims (3x)": 6.00, "Final": 3.00, "Total": 9.00, "note": "Possible larger final or 4th interim"},
            "macro_sensitivity": "Soft-landing + AI capex boom is the upside case.",
        },
    },
    "calendar_notes": "Multiple interims + final. CY DPS mixes current interims + prior final.",
    "risks": ["China export controls", "Semi cycle", "High valuation"],
    "upside_triggers": ["Further guidance raise", "Larger buyback", "Payout ratio lift"],
    "news_log": [
        {"date": "2026-07-15", "source": "Company PR", "text": "Q2 sales €9.3bn, GM 54%. Raised FY26 sales to €43-45bn. Interim DPS €1.88. Buybacks ongoing.", "impact": "bullish", "category": "Results"},
    ],
    "transcript_insights": {
        "event": "Q2 2026 Investor Call", "date": "2026-07-15", "source": "Company IR",
        "key_points": ["Interim €1.88 confirmed", "Guidance raised", "Buyback ongoing", "No policy change"],
        "dps_relevant_quotes": ["An interim dividend over 2026 of €1.88 per ordinary share will be made payable on August 5, 2026."],
        "impact_on_scenarios": "Supports base and bull; progressive policy reiterated.",
    },
    "historical_policy": "Progressive multi-interim + final. Payout typically ~25-35% of earnings. Net cash supports flexibility.",
    "payout_range": "25–35% of net income (target zone)",
}

SAMPLE_UNIVERSE["SAN.MC"] = {
    "name": "Banco Santander", "country": "ES", "sector": "Banks", "fy_end": "12-31", "currency": "EUR",
    "policy": "Semi-annual (ordinary ~50% of underlying, split cash/buyback)",
    "policy_flag": "Watch: excess capital distributions / higher buybacks vs cash DPS",
    "shares_m": 15500.0, "last_reported": "H1'26 (22 Jul)", "reported_eps_ytd": 0.47,
    "eps": {"FY25a": 0.75, "FY26e": 0.90, "FY27e": 0.98, "FY28e": 1.05},
    "dps_hist": {"FY23": 0.195, "FY24": 0.21, "FY25": 0.24},
    "consensus_dps": {"FY26e": 0.30, "FY27e": 0.34, "FY28e": 0.38},
    "payout_target": 0.50, "fcf_cover": None, "net_debt_ebitda": None, "price": 13.0, "is_bank": True,
    "scenarios": {
        "bear": {
            "FY26e": 0.26, "FY27e": 0.28, "FY28e": 0.30,
            "rationale": "Higher CoR / slower growth → cash DPS grows slowly, more via buybacks",
            "eps_rationale": "NII pressure + higher provisions. Underlying profit still grows but slower.",
            "breakdown": {"Interim": 0.12, "Final": 0.14, "Total": 0.26, "note": "Cash component; buybacks extra"},
            "macro_sensitivity": "Credit cycle / LatAm FX. CET1 buffer exists but high payout leaves less margin of error in deep stress.",
        },
        "base": {
            "FY26e": 0.30, "FY27e": 0.34, "FY28e": 0.38,
            "rationale": "H1 underlying +15%, CET1 14%, on track for ≥€10bn buybacks 25-26",
            "eps_rationale": "Continued mid-teens RoTE, controlled CoR, capital generation funds distributions.",
            "breakdown": {"Interim": 0.14, "Final": 0.16, "Total": 0.30, "note": "~50% ordinary (cash+buyback)"},
            "macro_sensitivity": "Moderate. Excess capital and buybacks give flexibility; cash DPS progressive.",
        },
        "bull": {
            "FY26e": 0.38, "FY27e": 0.45, "FY28e": 0.55,
            "rationale": "Excess capital specials + higher cash payout",
            "eps_rationale": "Strong capital generation + lower CoR → room for higher cash DPS or specials.",
            "breakdown": {"Interim": 0.16, "Final": 0.22, "Total": 0.38, "note": "Possible special on top"},
            "macro_sensitivity": "Soft-landing / lower rates support NII and asset quality.",
        },
    },
    "calendar_notes": "Interim ~Nov, final ~May. Buybacks are not DPS but support EPS.",
    "risks": ["LatAm FX/politics", "NII sensitivity", "Regulation"],
    "upside_triggers": ["CET1 well above target → special / higher cash DPS"],
    "news_log": [
        {"date": "2026-07-22", "source": "H1 Results", "text": "Underlying profit €7.3bn (+15%), RoTE 15.6%, CET1 14.0%. ≥€10bn buybacks 2025-26 on track.", "impact": "bullish capital return", "category": "Results"},
    ],
    "transcript_insights": {
        "event": "H1 2026 Earnings Call", "date": "2026-07-22", "source": "Company",
        "key_points": ["Record H1", "Ordinary ~50% underlying", "Buyback commitment on track"],
        "dps_relevant_quotes": ["ordinary shareholder remuneration policy ... approximately 50% of the Group’s underlying profit."],
        "impact_on_scenarios": "Supports base DPS + strong total yield via buybacks.",
    },
    "historical_policy": "Ordinary ~50% of underlying (cash + buybacks). Excess capital returned at period-end if available. High total distribution but cash DPS is only part of it.",
    "payout_range": "~50% of underlying profit (cash + buybacks combined)",
}

SAMPLE_UNIVERSE["AIR.PA"] = {
    "name": "Airbus", "country": "FR/NL", "sector": "Industrials", "fy_end": "12-31", "currency": "EUR",
    "policy": "Annual (final)", "policy_flag": None, "shares_m": 790.0, "last_reported": "H1'26 (29 Jul)",
    "reported_eps_ytd": 2.84,
    "eps": {"FY25a": 5.80, "FY26e": 6.80, "FY27e": 8.20, "FY28e": 9.80},
    "dps_hist": {"FY23": 1.80, "FY24": 2.00, "FY25": 2.20},
    "consensus_dps": {"FY26e": 2.50, "FY27e": 2.90, "FY28e": 3.40},
    "payout_target": 0.35, "fcf_cover": 1.4, "net_debt_ebitda": 0.3, "price": 215.0, "is_bank": False,
    "scenarios": {
        "bear": {
            "FY26e": 2.20, "FY27e": 2.40, "FY28e": 2.60,
            "rationale": "Delivery delays / supply chain → weaker FCF, conservative payout",
            "eps_rationale": "Ramp issues, inventory build persists, FCF lags. EPS still grows but slower.",
            "breakdown": {"Final only": 2.20, "Total": 2.20, "note": "Paid following spring"},
            "macro_sensitivity": "Supply chain + airline demand. Working-capital drag is the near-term risk.",
        },
        "base": {
            "FY26e": 2.50, "FY27e": 2.90, "FY28e": 3.40,
            "rationale": "H1 351 deliveries, guidance unchanged (~870 a/c, EBIT adj ~€7.5bn, FCF ~€4.5bn)",
            "eps_rationale": "Guidance held; progressive recovery in FCF as inventory normalises.",
            "breakdown": {"Final only": 2.50, "Total": 2.50, "note": "Standard annual final"},
            "macro_sensitivity": "Moderate. Guidance buffer exists; FCF timing is the watchpoint.",
        },
        "bull": {
            "FY26e": 2.90, "FY27e": 3.60, "FY28e": 4.50,
            "rationale": "Ramp success + higher FCF conversion → accelerated DPS growth",
            "eps_rationale": "Delivery beat + better working capital → FCF overshoot supports higher DPS.",
            "breakdown": {"Final only": 2.90, "Total": 2.90, "note": "Possible special if FCF overshoots"},
            "macro_sensitivity": "Soft-landing + strong traffic supports airline orders and pricing.",
        },
    },
    "calendar_notes": "Annual final paid in following calendar year → CY DPS ≈ prior FY DPS.",
    "risks": ["Supply chain (engines)", "Working-capital drag", "Geopolitics"],
    "upside_triggers": ["Delivery guidance raise", "FCF beat"],
    "news_log": [
        {"date": "2026-07-29", "source": "H1 Results", "text": "351 deliveries. Guidance unchanged. FCF negative on inventory build.", "impact": "base", "category": "Results"},
    ],
    "transcript_insights": None,
    "historical_policy": "Annual final, progressive. Payout typically 30-40% of earnings once FCF normalises.",
    "payout_range": "30–40% of net income (illustrative once FCF stabilises)",
}

# Add more rich-ish / light names for Euro Stoxx core + extras
extra = [
    ("MC.PA", "LVMH", "FR", "Consumer Discretionary", "EUR", "Annual (final)", 0.45, 13.0, 14.0, 15.0, 460.0, False, "Luxury; progressive but discretionary"),
    ("SIE.DE", "Siemens", "DE", "Industrials", "EUR", "Annual (final)", 0.45, 5.20, 5.60, 6.00, 285.0, False, ""),
    ("SAP.DE", "SAP", "DE", "Technology", "EUR", "Annual (final)", 0.40, 2.35, 2.60, 2.90, 170.0, False, ""),
    ("OR.PA", "L'Oréal", "FR", "Consumer Staples", "EUR", "Annual (final)", 0.55, 7.00, 7.50, 8.10, 385.0, False, ""),
    ("ITX.MC", "Inditex", "ES", "Consumer Discretionary", "EUR", "Semi-annual", 0.70, 1.20, 1.35, 1.50, 58.0, False, ""),
    ("SU.PA", "Schneider Electric", "FR", "Industrials", "EUR", "Annual (final)", 0.45, 4.00, 4.40, 4.80, 310.0, False, ""),
    ("RMS.PA", "Hermès", "FR", "Consumer Discretionary", "EUR", "Annual (final)", 0.35, 15.0, 17.0, 19.0, 2200.0, False, "Very progressive, low payout"),
    ("TTE.PA", "TotalEnergies", "FR", "Energy", "EUR", "Quarterly (progressive)", 0.50, 3.40, 3.55, 3.70, 58.0, False, "Energy; progressive + buybacks"),
    ("ALV.DE", "Allianz", "DE", "Insurance", "EUR", "Annual (final)", 0.55, 15.0, 16.0, 17.0, 440.0, False, ""),
    ("SAF.PA", "Safran", "FR", "Industrials", "EUR", "Annual (final)", 0.40, 2.80, 3.20, 3.70, 280.0, False, ""),
    ("BBVA.MC", "BBVA", "ES", "Banks", "EUR", "Semi-annual", 0.50, 0.70, 0.78, 0.85, 12.5, True, "Bank – less sensitive yield flag"),
    ("ABI.BR", "AB InBev", "BE", "Consumer Staples", "EUR", "Annual (final)", 0.45, 1.00, 1.10, 1.20, 58.0, False, ""),
    ("DTE.DE", "Deutsche Telekom", "DE", "Telecom", "EUR", "Annual (final)", 0.50, 0.90, 0.95, 1.00, 28.0, False, ""),
    ("IBE.MC", "Iberdrola", "ES", "Utilities", "EUR", "Semi-annual / interim", 0.65, 0.60, 0.64, 0.68, 14.0, False, ""),
    ("UCG.MI", "UniCredit", "IT", "Banks", "EUR", "Semi-annual", 0.50, 1.80, 2.00, 2.20, 55.0, True, "Bank"),
    ("BNP.PA", "BNP Paribas", "FR", "Banks", "EUR", "Annual (final)", 0.50, 5.00, 5.40, 5.80, 75.0, True, "Bank"),
    ("ISP.MI", "Intesa Sanpaolo", "IT", "Banks", "EUR", "Semi-annual", 0.70, 0.35, 0.38, 0.42, 4.5, True, "Bank – high payout"),
    ("AI.PA", "Air Liquide", "FR", "Materials", "EUR", "Annual (final)", 0.50, 3.30, 3.50, 3.75, 170.0, False, ""),
    ("ENEL.MI", "Enel", "IT", "Utilities", "EUR", "Semi-annual", 0.65, 0.45, 0.48, 0.52, 7.0, False, ""),
    ("CS.PA", "AXA", "FR", "Insurance", "EUR", "Annual (final)", 0.55, 2.15, 2.30, 2.45, 35.0, False, ""),
    ("SAN.PA", "Sanofi", "FR", "Health Care", "EUR", "Annual (final)", 0.50, 3.80, 4.00, 4.20, 95.0, False, ""),
    ("INGA.AS", "ING Groep", "NL", "Banks", "EUR", "Semi-annual / interim", 0.50, 1.10, 1.20, 1.30, 18.0, True, "Bank"),
    ("IFX.DE", "Infineon", "DE", "Technology", "EUR", "Annual (final)", 0.30, 0.45, 0.55, 0.65, 35.0, False, ""),
    ("ENI.MI", "ENI", "IT", "Energy", "EUR", "Semi-annual / quarterly", 0.45, 1.00, 1.05, 1.10, 15.0, False, ""),
    ("DG.PA", "Vinci", "FR", "Industrials", "EUR", "Annual (final)", 0.50, 5.00, 5.40, 5.80, 115.0, False, ""),
    ("RACE.MI", "Ferrari", "IT", "Consumer Discretionary", "EUR", "Annual (final)", 0.35, 2.50, 2.80, 3.20, 420.0, False, ""),
    ("MUV2.DE", "Munich Re", "DE", "Insurance", "EUR", "Annual (final)", 0.45, 16.0, 17.5, 19.0, 480.0, False, ""),
    ("DBK.DE", "Deutsche Bank", "DE", "Banks", "EUR", "Annual (final)", 0.40, 1.00, 1.20, 1.40, 18.0, True, "Bank"),
    ("DHL.DE", "DHL Group", "DE", "Industrials", "EUR", "Annual (final)", 0.50, 2.00, 2.15, 2.30, 42.0, False, ""),
    ("RHM.DE", "Rheinmetall", "DE", "Industrials", "EUR", "Annual (final)", 0.30, 6.00, 8.00, 10.00, 950.0, False, "Defence – growth prioritised"),
    ("BAS.DE", "BASF", "DE", "Materials", "EUR", "Annual (final)", 0.55, 2.25, 2.40, 2.60, 48.0, False, ""),
    ("BAYN.DE", "Bayer", "DE", "Health Care", "EUR", "Annual (final)", 0.40, 0.11, 0.50, 1.00, 28.0, False, "Litigation overhang – low near-term DPS"),
    ("ADS.DE", "Adidas", "DE", "Consumer Discretionary", "EUR", "Annual (final)", 0.40, 1.00, 1.40, 1.80, 220.0, False, ""),
    ("BMW.DE", "BMW", "DE", "Consumer Discretionary", "EUR", "Annual (final)", 0.35, 4.50, 4.80, 5.20, 90.0, False, ""),
    ("MBG.DE", "Mercedes-Benz", "DE", "Consumer Discretionary", "EUR", "Annual (final)", 0.40, 4.30, 4.50, 4.70, 60.0, False, ""),
    ("STLAM.MI", "Stellantis", "NL/IT", "Consumer Discretionary", "EUR", "Semi-annual", 0.30, 1.00, 1.10, 1.20, 12.0, False, "Auto – cyclical"),
    ("RNO.PA", "Renault", "FR", "Consumer Discretionary", "EUR", "Annual (final)", 0.25, 1.50, 2.00, 2.50, 45.0, False, "Auto – recovery"),
    ("ENGI.PA", "Engie", "FR", "Utilities", "EUR", "Semi-annual / interim", 0.65, 1.40, 1.50, 1.60, 16.0, False, "Utility – regulated + energy"),
    ("VIE.PA", "Veolia", "FR", "Utilities", "EUR", "Annual (final)", 0.55, 1.40, 1.50, 1.65, 30.0, False, "Utility / environment"),
]

for t, name, cty, sec, cur, pol, po, d26, d27, d28, px, bank, note in extra:
    SAMPLE_UNIVERSE[t] = make_light(name, t, cty, sec, cur, pol, po, d26, d27, d28, price=px, is_bank=bank, notes=note)

# Keep Nestlé & Shell as useful extras
SAMPLE_UNIVERSE["NESN.SW"] = {
    "name": "Nestlé", "country": "CH", "sector": "Food, Beverage & Tobacco", "fy_end": "12-31", "currency": "CHF",
    "policy": "Semi-annual (interim + final)", "policy_flag": None, "shares_m": 2600.0,
    "last_reported": "H1'26", "reported_eps_ytd": 2.10,
    "eps": {"FY25a": 4.80, "FY26e": 5.05, "FY27e": 5.35, "FY28e": 5.70},
    "dps_hist": {"FY23": 3.00, "FY24": 3.15, "FY25": 3.30},
    "consensus_dps": {"FY26e": 3.45, "FY27e": 3.65, "FY28e": 3.90},
    "payout_target": 0.65, "fcf_cover": 1.3, "net_debt_ebitda": 1.8, "price": 85.0, "is_bank": False,
    "scenarios": {
        "bear": {"FY26e": 3.30, "FY27e": 3.40, "FY28e": 3.50, "rationale": "Volume/FX pressure + restructuring", "eps_rationale": "Organic growth soft, one-offs", "breakdown": {"Interim": 1.50, "Final": 1.80, "Total": 3.30, "note": ""}, "macro_sensitivity": "FX + commodities"},
        "base": {"FY26e": 3.45, "FY27e": 3.65, "FY28e": 3.90, "rationale": "H1 OG 3.6%, guidance 3-4%", "eps_rationale": "In-line progressive", "breakdown": {"Interim": 1.55, "Final": 1.90, "Total": 3.45, "note": ""}, "macro_sensitivity": "Defensive"},
        "bull": {"FY26e": 3.60, "FY27e": 3.90, "FY28e": 4.30, "rationale": "Stronger RIG + cost savings", "eps_rationale": "Margin recovery", "breakdown": {"Interim": 1.60, "Final": 2.00, "Total": 3.60, "note": ""}, "macro_sensitivity": "Soft landing helps"},
    },
    "calendar_notes": "Interim typically Aug/Sep, final Apr/May.",
    "risks": ["Commodity", "FX"], "upside_triggers": ["Margin acceleration"],
    "news_log": [], "transcript_insights": None,
    "historical_policy": "Long progressive history. Payout typically 60-70%.",
    "payout_range": "60–70% of underlying EPS",
}

SAMPLE_UNIVERSE["SHEL.L"] = {
    "name": "Shell", "country": "GB", "sector": "Energy", "fy_end": "12-31", "currency": "USD",
    "policy": "Quarterly (progressive ~4% p.a.)", "policy_flag": None, "shares_m": 6200.0,
    "last_reported": "Q2'26", "reported_eps_ytd": 2.94,
    "eps": {"FY25a": 3.40, "FY26e": 3.80, "FY27e": 3.60, "FY28e": 3.70},
    "dps_hist": {"FY23": 1.29, "FY24": 1.38, "FY25": 1.45},
    "consensus_dps": {"FY26e": 1.56, "FY27e": 1.62, "FY28e": 1.70},
    "payout_target": 0.40, "fcf_cover": 2.8, "net_debt_ebitda": 0.5, "price": 32.0, "is_bank": False,
    "scenarios": {
        "bear": {"FY26e": 1.48, "FY27e": 1.40, "FY28e": 1.30, "rationale": "Oil soft + higher capex", "eps_rationale": "Lower CFFO", "breakdown": {"Q1": 0.37, "Q2": 0.37, "Q3": 0.37, "Q4": 0.37, "Total": 1.48, "note": ""}, "macro_sensitivity": "Oil price"},
        "base": {"FY26e": 1.56, "FY27e": 1.62, "FY28e": 1.70, "rationale": "Progressive 4%, strong CFFO, buybacks", "eps_rationale": "40-50% of CFFO distributed", "breakdown": {"Q1": 0.39, "Q2": 0.39, "Q3": 0.39, "Q4": 0.39, "Total": 1.56, "note": ""}, "macro_sensitivity": "Resilient"},
        "bull": {"FY26e": 1.70, "FY27e": 1.85, "FY28e": 2.00, "rationale": "Higher distribution ratio", "eps_rationale": "Strong FCF", "breakdown": {"Q1": 0.39, "Q2": 0.39, "Q3": 0.42, "Q4": 0.50, "Total": 1.70, "note": ""}, "macro_sensitivity": "Higher oil"},
    },
    "calendar_notes": "Quarterly lag ~1 quarter.",
    "risks": ["Oil price", "Transition"], "upside_triggers": ["Buyback increase"],
    "news_log": [], "transcript_insights": None,
    "historical_policy": "Progressive quarterly ~4% annual increase + 40-50% of CFFO via DPS+buybacks.",
    "payout_range": "40–50% of CFFO (DPS + buybacks)",
}

# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
_APP_DIR = Path(__file__).parent
DATA_PATH = _APP_DIR / "user_data.json"
ALERTS_PATH = _APP_DIR / "daily_alerts.json"
HARD_EPS_PATH = _APP_DIR / "hard_eps.json"

def load_json(path, default=None):
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

def get_stock_data(ticker: str) -> dict:
    base = deepcopy(SAMPLE_UNIVERSE.get(ticker, {}))
    user = load_json(DATA_PATH).get(ticker, {})
    if "scenarios" in user:
        base["scenarios"] = user["scenarios"]
    if "news_log" in user:
        base["news_log"] = user.get("news_log", []) + base.get("news_log", [])
    if "policy_flag" in user:
        base["policy_flag"] = user["policy_flag"]
    if "eps" in user:
        base["eps"].update(user["eps"])
    return base

def get_hard_eps(ticker):
    hard = load_json(HARD_EPS_PATH)
    if ticker in hard:
        return hard[ticker]
    s = SAMPLE_UNIVERSE.get(ticker, {})
    return s.get("eps", {})

def save_hard_eps(ticker, eps_dict):
    hard = load_json(HARD_EPS_PATH)
    hard[ticker] = eps_dict
    save_json(HARD_EPS_PATH, hard)

# ---------------------------------------------------------------------------
# Yield Red-Flag
# ---------------------------------------------------------------------------
def yield_flag(stock: dict) -> dict:
    price = stock.get("price") or 50.0
    dps = stock["scenarios"]["base"]["FY26e"]
    yld = (dps / price * 100) if price else 0.0
    is_bank = stock.get("is_bank", False)
    fcf = stock.get("fcf_cover")
    payout = stock.get("payout_target") or 0.5
    hist = stock.get("dps_hist", {})
    hist_vals = [v for v in hist.values() if isinstance(v, (int, float))]
    avg_hist_dps = np.mean(hist_vals) if hist_vals else dps * 0.9
    hist_yld = (avg_hist_dps / price * 100) if price else yld

    level = "green"
    msgs = []

    if yld > hist_yld + 1.5:
        level = "amber"
        msgs.append(f"Yield {yld:.1f}% is >1.5 pts above recent history (~{hist_yld:.1f}%)")

    if yld > 7.0 and (fcf is not None and fcf < 1.3 or payout > 0.80):
        level = "red"
        msgs.append(f"High absolute yield {yld:.1f}% + thin cover / high payout – classic cut-risk zone")

    if payout >= 0.90:
        if is_bank:
            if level == "green":
                level = "amber"
            msgs.append("Very high payout / thin earnings buffer (bank). Macro stress could force rapid rebase (BMPS-style risk). Less sensitive flag because buybacks often absorb excess.")
        else:
            level = "red" if level != "red" else level
            msgs.append("Payout ≥90% – thin buffer; stress could force rebase")

    if yld > 5.5 and fcf is not None and fcf > 1.8 and (stock.get("net_debt_ebitda") or 0) < 1.5:
        if level == "amber":
            msgs.append("Yield elevated but well covered by FCF and low leverage – less immediate cut risk")

    if not msgs:
        msgs.append("Yield and cover look unremarkable vs history/policy")

    return {
        "level": level,
        "yield_pct": round(yld, 2),
        "hist_yield_pct": round(hist_yld, 2),
        "messages": msgs,
        "fcf_cover": fcf,
        "payout_target": payout,
    }

# ---------------------------------------------------------------------------
# Calendar DPS
# ---------------------------------------------------------------------------
def compute_calendar_dps(stock: dict) -> dict:
    policy = stock.get("policy", "").lower()
    scen = stock["scenarios"]
    if "quarter" in policy:
        return {
            "bear": round(0.75 * scen["bear"]["FY26e"] + 0.25 * scen["bear"].get("FY27e", scen["bear"]["FY26e"]), 3),
            "base": round(0.75 * scen["base"]["FY26e"] + 0.25 * scen["base"].get("FY27e", scen["base"]["FY26e"]), 3),
            "bull": round(0.75 * scen["bull"]["FY26e"] + 0.25 * scen["bull"].get("FY27e", scen["bull"]["FY26e"]), 3),
            "note": "Illustrative lag: ~¾ of FY26 + ¼ of FY27 for CY27.",
        }
    elif "semi" in policy or "interim" in policy:
        return {
            "bear": round(0.5 * scen["bear"]["FY26e"] + 0.5 * scen["bear"].get("FY27e", 0), 3),
            "base": round(0.5 * scen["base"]["FY26e"] + 0.5 * scen["base"].get("FY27e", 0), 3),
            "bull": round(0.5 * scen["bull"]["FY26e"] + 0.5 * scen["bull"].get("FY27e", 0), 3),
            "note": "Mix of prior final + current interim.",
        }
    else:
        return {
            "bear": scen["bear"]["FY26e"],
            "base": scen["base"]["FY26e"],
            "bull": scen["bull"]["FY26e"],
            "note": "Annual final typically paid next calendar year.",
        }

def adjust_scenarios_from_eps(stock: dict, new_eps: dict, payout_mult: float = 1.0):
    old_eps = stock["eps"]
    for case in ["bear", "base", "bull"]:
        for yr in ["FY26e", "FY27e", "FY28e"]:
            if yr in new_eps and yr in old_eps and old_eps[yr]:
                scale = (new_eps[yr] / old_eps[yr]) * payout_mult
                old_val = stock["scenarios"][case][yr]
                stock["scenarios"][case][yr] = round(old_val * scale, 3)
                bd = stock["scenarios"][case].get("breakdown", {})
                if "Total" in bd:
                    for k in list(bd.keys()):
                        if k not in ("note", "Total") and isinstance(bd[k], (int, float)):
                            bd[k] = round(bd[k] * scale, 3)
                    bd["Total"] = stock["scenarios"][case][yr]
    stock["eps"].update(new_eps)
    return stock

def generate_daily_alerts():
    today = date.today().isoformat()
    alerts = {
        "generated_at": datetime.now().isoformat(),
        "scan_date": today,
        "categories": {
            "Results": [],
            "Capital Return": [],
            "Policy / Payout": [],
            "One-offs / Corporate Actions": [],
            "Consensus / Research": [],
            "Market Chatter": [],
            "DPS Forecast Changes": [],
            "Yield Watch": [],
        },
        "summary": [],
    }

    alerts["categories"]["Results"].extend([
        {"ticker": "ASML.AS", "date": "2026-07-15", "headline": "Q2 beat + FY26 sales guidance raised", "impact": "EPS up → support higher DPS", "action": "Review base/bull"},
        {"ticker": "SAN.MC", "date": "2026-07-22", "headline": "H1 underlying +15%, CET1 14%, buybacks on track", "impact": "Capital return strong", "action": "Watch specials"},
        {"ticker": "AIR.PA", "date": "2026-07-29", "headline": "H1 deliveries + guidance held; FCF inventory drag", "impact": "Base held", "action": "Monitor FCF"},
        {"ticker": "SHEL.L", "date": "2026-07-30", "headline": "Strong CFFO, progressive DPS, new buyback", "impact": "Supports base", "action": "–"},
    ])
    alerts["categories"]["Capital Return"].extend([
        {"ticker": "ASML.AS", "date": "2026-08-05", "headline": "Interim €1.88 paid; buyback active", "impact": "Positive total yield", "action": "Update calendar"},
        {"ticker": "SAN.MC", "date": "2026-07-22", "headline": "c.€9bn of ≥€10bn buyback commitment delivered/approved", "impact": "Excess capital returning", "action": "–"},
    ])

    for t, s in SAMPLE_UNIVERSE.items():
        yf = yield_flag(s)
        if yf["level"] in ("amber", "red"):
            alerts["categories"]["Yield Watch"].append({
                "ticker": t,
                "date": today,
                "headline": f"{s['name']}: yield {yf['yield_pct']}% – {yf['level'].upper()}",
                "impact": "; ".join(yf["messages"][:2]),
                "action": "Review cover & policy",
            })

    user = load_json(DATA_PATH)
    for t, u in user.items():
        if u.get("dps_change_log"):
            for ch in u["dps_change_log"][-3:]:
                alerts["categories"]["DPS Forecast Changes"].append({
                    "ticker": t, "date": ch.get("date", today),
                    "headline": ch.get("text", "DPS forecast changed"),
                    "impact": ch.get("impact", ""),
                    "action": "Confirm vs consensus",
                })

    alerts["summary"] = [
        f"{today}: Morning scan completed for Euro Stoxx 50 core + extras.",
        f"Yield Watch: {len(alerts['categories']['Yield Watch'])} names flagged amber/red.",
        "Highest near-term DPS relevance: ASML interim + guidance; Santander capital return; Shell progressive + buybacks.",
        "Action: review Yield Watchlist and any DPS Forecast Changes.",
    ]
    save_json(ALERTS_PATH, alerts)
    return alerts

def load_or_generate_alerts():
    alerts = load_json(ALERTS_PATH)
    if not alerts or alerts.get("scan_date") != date.today().isoformat():
        alerts = generate_daily_alerts()
    return alerts

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Euro Stoxx 50 DPS Scenario Tracker", layout="wide", page_icon="📈")

st.title("📈 Euro Stoxx 50 DPS Scenario Tracker")
st.caption("Bear / Base / Bull · Payment-pattern breakdowns · Yield Red-Flag · Simulate/Reset EPS · Morning newsflow · Prototype")

with st.sidebar:
    st.header("Universe")
    tickers = sorted(SAMPLE_UNIVERSE.keys())
    names = [f"{t} – {SAMPLE_UNIVERSE[t]['name']}" for t in tickers]
    choice = st.selectbox("Select stock", names, index=0)
    ticker = choice.split(" – ")[0]

    st.markdown("---")
    stock = get_stock_data(ticker)
    yf = yield_flag(stock)
    flag_emoji = {"green": "🟢", "amber": "🟠", "red": "🔴"}.get(yf["level"], "⚪")
    st.markdown(f"**Yield flag:** {flag_emoji} {yf['level'].upper()} ({yf['yield_pct']}%)")
    if stock.get("policy_flag"):
        st.warning(f"⚠️ Policy flag: {stock['policy_flag']}")
    else:
        st.success("No active policy-change flag")
    st.markdown(f"**Policy:** {stock.get('policy')}")
    st.markdown(f"**FCF cover:** {stock.get('fcf_cover')}")
    st.markdown(f"**Payout target:** {stock.get('payout_target')}")

    st.markdown("---")
    if st.button("🔄 Run Morning Scan", type="primary"):
        generate_daily_alerts()
        st.success("Morning intelligence refreshed")
        st.rerun()

    st.caption(f"{len(SAMPLE_UNIVERSE)} names · Euro Stoxx 50 core + Stellantis, Renault, Engie, Veolia + Nestlé/Shell")

stock = get_stock_data(ticker)
col1, col2, col3, col4 = st.columns([2.2, 1, 1, 1])
with col1:
    st.subheader(f"{stock['name']} ({ticker})")
    st.markdown(f"{stock['sector']} · {stock['country']} · {stock['currency']}")
with col2:
    st.metric("Cons. DPS FY26e", f"{stock['consensus_dps']['FY26e']:.2f}")
with col3:
    st.metric("Yield (base)", f"{yf['yield_pct']:.1f}%")
with col4:
    st.metric("Flag", f"{flag_emoji} {yf['level'].upper()}")

tab_alerts, tab_yield, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚨 Daily Alerts",
    "⚠️ Yield Watch",
    "📊 Scenarios + Breakdown",
    "📅 Calendar vs FY",
    "🔄 EPS Simulate / Reset",
    "📰 News / Policy",
    "📋 Universe",
])

with tab_alerts:
    alerts = load_or_generate_alerts()
    st.markdown(f"### Morning Intelligence · **{alerts.get('scan_date', '–')}**")
    st.caption(f"Generated {alerts.get('generated_at', '–')}")
    for s in alerts.get("summary", []):
        st.markdown(f"- {s}")
    st.markdown("---")
    for cat, items in alerts.get("categories", {}).items():
        if not items:
            continue
        with st.expander(f"**{cat}** ({len(items)})", expanded=(cat in ("Results", "Yield Watch", "DPS Forecast Changes"))):
            for it in items:
                st.markdown(f"**{it.get('ticker','')}** · {it.get('date','')}")
                st.markdown(it.get("headline", ""))
                st.caption(f"Impact: {it.get('impact','')} | Action: {it.get('action','')}")

with tab_yield:
    st.markdown("### Yield Red-Flag Watchlist")
    st.caption("High yield is a warning, not automatic cut signal. Banks are treated less sensitively (buybacks often absorb excess).")
    rows = []
    for t, s in SAMPLE_UNIVERSE.items():
        y = yield_flag(s)
        rows.append({
            "Ticker": t, "Name": s["name"], "Yield %": y["yield_pct"],
            "Hist ~%": y["hist_yield_pct"], "Flag": y["level"].upper(),
            "FCF cover": y["fcf_cover"], "Payout tgt": y["payout_target"],
            "Note": y["messages"][0] if y["messages"] else "",
        })
    dfy = pd.DataFrame(rows).sort_values(["Flag", "Yield %"], ascending=[True, False])
    st.dataframe(dfy, use_container_width=True, hide_index=True)

    st.markdown(f"#### Current name: {stock['name']}")
    for m in yf["messages"]:
        st.markdown(f"- {m}")
    st.markdown(f"**Historical policy:** {stock.get('historical_policy', '–')}")
    st.markdown(f"**Payout range / target:** {stock.get('payout_range', '–')}")

with tab1:
    st.markdown("### Bear / Base / Bull DPS + Pattern Breakdown + EPS rationale")
    scen = stock["scenarios"]
    df_scen = pd.DataFrame({
        "Case": ["Bear", "Base", "Bull"],
        "FY26e": [scen["bear"]["FY26e"], scen["base"]["FY26e"], scen["bull"]["FY26e"]],
        "FY27e": [scen["bear"]["FY27e"], scen["base"]["FY27e"], scen["bull"]["FY27e"]],
        "FY28e": [scen["bear"]["FY28e"], scen["base"]["FY28e"], scen["bull"]["FY28e"]],
        "Rationale": [scen["bear"].get("rationale",""), scen["base"].get("rationale",""), scen["bull"].get("rationale","")],
    })
    st.dataframe(df_scen, use_container_width=True, hide_index=True)

    for case, label in [("bear", "Bear"), ("base", "Base"), ("bull", "Bull")]:
        with st.expander(f"**{label}** – Total FY26e {scen[case]['FY26e']:.3f} {stock['currency']}", expanded=(case=="base")):
            st.markdown(f"**DPS rationale:** {scen[case].get('rationale','–')}")
            st.markdown(f"**EPS path / fundamentals:** {scen[case].get('eps_rationale','–')}")
            st.markdown(f"**Macro sensitivity:** {scen[case].get('macro_sensitivity','–')}")
            bd = scen[case].get("breakdown", {})
            cols = st.columns(max(len([k for k in bd if k not in ("note","Total")]), 1))
            i = 0
            for k, v in bd.items():
                if k in ("note", "Total"):
                    continue
                cols[i % len(cols)].metric(k, f"{v:.3f}" if isinstance(v, (int, float)) else v)
                i += 1
            if bd.get("note"):
                st.caption(bd["note"])

    st.markdown(f"**Historical policy reminder:** {stock.get('historical_policy','–')}")
    st.markdown(f"**Payout range / DPS target:** {stock.get('payout_range','–')}")

    fig = go.Figure()
    years = ["FY26e", "FY27e", "FY28e"]
    for case, color in [("bear", "#ef4444"), ("base", "#3b82f6"), ("bull", "#22c55e")]:
        fig.add_trace(go.Scatter(x=years, y=[scen[case][y] for y in years], mode="lines+markers",
                                 name=case.capitalize(), line=dict(color=color, width=3)))
    fig.add_trace(go.Scatter(x=years, y=[stock["consensus_dps"].get(y) for y in years],
                             mode="markers", name="Consensus", marker=dict(symbol="diamond", size=12, color="black")))
    fig.update_layout(title="DPS Scenario Paths", yaxis_title=f"DPS ({stock['currency']})", height=360, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### Calendar-year DPS (dividend-futures relevant)")
    cal = compute_calendar_dps(stock)
    c1, c2, c3 = st.columns(3)
    c1.metric("Bear CY", f"{cal['bear']:.3f}")
    c2.metric("Base CY", f"{cal['base']:.3f}")
    c3.metric("Bull CY", f"{cal['bull']:.3f}")
    st.caption(cal["note"])
    st.markdown(f"**Company note:** {stock.get('calendar_notes','')}")
    if stock.get("policy_flag"):
        st.warning(f"⚠️ Active policy flag: **{stock['policy_flag']}**")

with tab3:
    st.markdown("### EPS Simulate + Reset to hard data")
    st.markdown("Edit EPS → **Simulate** recalculates DPS scenarios & breakdowns. **Reset** restores last saved hard/official EPS so overrides are never permanent by accident.")

    hard = get_hard_eps(ticker)
    cur_eps = stock["eps"]

    c1, c2, c3 = st.columns(3)
    with c1:
        e26 = st.number_input("FY26e EPS", value=float(cur_eps.get("FY26e", 0)), format="%.3f", key="e26")
    with c2:
        e27 = st.number_input("FY27e EPS", value=float(cur_eps.get("FY27e", 0)), format="%.3f", key="e27")
    with c3:
        e28 = st.number_input("FY28e EPS", value=float(cur_eps.get("FY28e", 0)), format="%.3f", key="e28")
    payout_mult = st.slider("Payout multiplier (1.0 = keep implied)", 0.7, 1.4, 1.0, 0.05)
    note = st.text_input("Note for change log (optional)")

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("▶ Simulate", type="primary"):
            new_eps = {"FY26e": e26, "FY27e": e27, "FY28e": e28}
            updated = adjust_scenarios_from_eps(deepcopy(stock), new_eps, payout_mult)
            user = load_json(DATA_PATH)
            user[ticker] = user.get(ticker, {})
            user[ticker]["eps"] = updated["eps"]
            user[ticker]["scenarios"] = updated["scenarios"]
            user[ticker].setdefault("dps_change_log", [])
            user[ticker]["dps_change_log"].insert(0, {
                "date": str(date.today()),
                "text": f"EPS simulated → DPS rescaled (×{payout_mult:.2f}). {note}",
                "impact": "User override",
            })
            save_json(DATA_PATH, user)
            st.success("Simulated. Scenarios updated.")
            st.rerun()
    with b2:
        if st.button("↺ Reset to hard data"):
            hard_eps = get_hard_eps(ticker)
            if not hard_eps:
                hard_eps = SAMPLE_UNIVERSE[ticker]["eps"]
            base = deepcopy(SAMPLE_UNIVERSE[ticker])
            updated = adjust_scenarios_from_eps(base, hard_eps, 1.0)
            user = load_json(DATA_PATH)
            user[ticker] = user.get(ticker, {})
            user[ticker]["eps"] = hard_eps
            user[ticker]["scenarios"] = updated["scenarios"]
            user[ticker].setdefault("dps_change_log", [])
            user[ticker]["dps_change_log"].insert(0, {
                "date": str(date.today()),
                "text": "Reset to hard/official EPS snapshot",
                "impact": "Reset",
            })
            save_json(DATA_PATH, user)
            st.success("Reset to hard data.")
            st.rerun()
    with b3:
        if st.button("💾 Save current as hard"):
            save_hard_eps(ticker, {"FY26e": e26, "FY27e": e27, "FY28e": e28})
            st.success("Saved as new hard EPS snapshot.")

    st.caption(f"Hard EPS snapshot: {hard or 'using sample defaults'}")

with tab4:
    st.markdown("### News, chatter, policy flags")
    for item in stock.get("news_log", [])[:10]:
        st.markdown(f"**{item.get('date')}** · *{item.get('source')}* · `{item.get('category', item.get('impact',''))}`")
        st.write(item.get("text", ""))
        st.markdown("---")
    with st.form("add_news"):
        ndate = st.date_input("Date", value=date.today())
        nsource = st.selectbox("Source", ["Company PR", "Results", "Sell-side", "Rumour / X / press", "Other"])
        ncat = st.selectbox("Category", ["Results", "Capital Return", "Policy / Payout", "One-offs / Corporate Actions", "Consensus / Research", "Market Chatter"])
        ntext = st.text_area("Comment / extract")
        nimpact = st.selectbox("Impact", ["neutral", "base", "bullish bias", "bearish bias", "policy flag"])
        nflag = st.text_input("Optional new policy_flag")
        if st.form_submit_button("Add to log") and ntext:
            user = load_json(DATA_PATH)
            user[ticker] = user.get(ticker, {})
            user[ticker].setdefault("news_log", [])
            user[ticker]["news_log"].insert(0, {"date": str(ndate), "source": nsource, "text": ntext, "impact": nimpact, "category": ncat})
            if nflag:
                user[ticker]["policy_flag"] = nflag
            save_json(DATA_PATH, user)
            st.success("Logged.")
            st.rerun()

with tab5:
    st.markdown("### Universe snapshot")
    rows = []
    for t, s in SAMPLE_UNIVERSE.items():
        y = yield_flag(s)
        rows.append({
            "Ticker": t, "Name": s["name"], "Sector": s["sector"],
            "Policy": (s.get("policy") or "")[:26],
            "DPS FY26e Base": s["scenarios"]["base"]["FY26e"],
            "Yield %": y["yield_pct"], "Flag": y["level"].upper(),
            "FY27e": s["scenarios"]["base"]["FY27e"],
            "FY28e": s["scenarios"]["base"]["FY28e"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(f"Total names: {len(SAMPLE_UNIVERSE)}")

st.markdown("---")
st.caption(f"Euro Stoxx 50 core + extras · illustrative data · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
