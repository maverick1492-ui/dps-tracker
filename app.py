"""
DPS Scenario Tracker for STOXX 600
- Bear/Base/Bull with full + interim/final/quarterly pattern breakdown
- Daily automated scan of results, PR, one-offs, buybacks, consensus & chatter
- Categorized morning alerts
- Earnings-call transcript insights
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import json
from pathlib import Path
from copy import deepcopy

# ----------------------
# SAMPLE DATA – updated with real mid-2026 events & pattern breakdowns
# ----------------------
SAMPLE_UNIVERSE = {
    "ASML.AS": {
        "name": "ASML Holding",
        "isin": "NL0010273215",
        "country": "NL",
        "sector": "Technology",
        "fy_end": "12-31",
        "currency": "EUR",
        "policy": "Multiple interims + final (progressive)",
        "policy_flag": None,
        "shares_m": 393.0,
        "last_reported": "Q2'26 (15 Jul)",
        "reported_eps_ytd": 7.4,
        "eps": {"FY25a": 24.73, "FY26e": 28.50, "FY27e": 33.00, "FY28e": 38.00},
        "dps_hist": {"FY23": 6.10, "FY24": 6.40, "FY25": 7.50},
        "consensus_dps": {"FY26e": 8.20, "FY27e": 9.60, "FY28e": 11.20},
        "payout_target": 0.30,
        "fcf_cover": 2.0,
        "net_debt_ebitda": -0.8,
        "scenarios": {
            "bear": {
                "FY26e": 7.40, "FY27e": 8.20, "FY28e": 9.00,
                "rationale": "Soft orders / China risk → slower growth, payout held",
                "breakdown": {"Interims (3x)": 5.20, "Final": 2.20, "Total": 7.40, "note": "Lower interims if guidance cut"}
            },
            "base": {
                "FY26e": 8.20, "FY27e": 9.60, "FY28e": 11.20,
                "rationale": "Raised 2026 sales guidance (€43-45bn) + progressive interims",
                "breakdown": {"Interims (3x)": 5.64, "Final": 2.56, "Total": 8.20, "note": "Current interim run-rate ~€1.88; further interims expected"}
            },
            "bull": {
                "FY26e": 9.00, "FY27e": 11.00, "FY28e": 13.50,
                "rationale": "AI demand continues + higher payout + specials from excess cash",
                "breakdown": {"Interims (3x)": 6.00, "Final": 3.00, "Total": 9.00, "note": "Possible 4th interim or larger final"}
            },
        },
        "calendar_notes": "Multiple interims paid within the year + final in following spring. CY DPS mixes current interims + prior final.",
        "risks": ["China export controls", "Semi cycle", "High valuation"],
        "upside_triggers": ["Further guidance raise", "Larger buyback", "Payout ratio lift"],
        "news_log": [
            {"date": "2026-07-15", "source": "Company PR", "text": "Q2 sales €9.3bn, GM 54%. Raised FY26 sales to €43-45bn / GM 54-56%. Interim DPS €1.88 payable 5 Aug. Buybacks ongoing (€1.1bn in Q2).", "impact": "bullish / EPS up / capital return", "category": "Results"},
            {"date": "2026-08-05", "source": "Company", "text": "Interim dividend of €1.88 paid. Buyback programme 2026-28 continues.", "impact": "capital return", "category": "Capital Return"},
        ],
        "transcript_insights": {
            "event": "Q2 2026 Investor Call",
            "date": "2026-07-15",
            "source": "Company IR transcript + Motley Fool",
            "key_points": [
                "Final 2025 DPS €2.70 paid in Q2; first 2026 interim €1.88 payable 5 Aug (2025 total DPS €7.50).",
                "Q2 buybacks €1.1bn under the 2026-28 programme; Q2 FCF €1.3bn.",
                "Guidance raised to sales €43-45bn supports sustained capital returns.",
                "Multi-interim + final structure confirmed; no policy change signalled.",
                "Installed Base and AI/logic/memory demand cited as cash-generation drivers.",
            ],
            "dps_relevant_quotes": [
                "An interim dividend over 2026 of €1.88 per ordinary share will be made payable on August 5, 2026.",
                "In the second quarter, we purchased around €1.1 billion worth of shares under the current 2026–2028 share buyback program.",
            ],
            "impact_on_scenarios": "Supports base and bull; interim already set; progressive policy reiterated.",
        },
    },
    "NESN.SW": {
        "name": "Nestlé",
        "isin": "CH0038863350",
        "country": "CH",
        "sector": "Food, Beverage & Tobacco",
        "fy_end": "12-31",
        "currency": "CHF",
        "policy": "Semi-annual (interim + final)",
        "policy_flag": None,
        "shares_m": 2600.0,
        "last_reported": "H1'26 (23-28 Jul)",
        "reported_eps_ytd": 2.10,
        "eps": {"FY25a": 4.80, "FY26e": 5.05, "FY27e": 5.35, "FY28e": 5.70},
        "dps_hist": {"FY23": 3.00, "FY24": 3.15, "FY25": 3.30},
        "consensus_dps": {"FY26e": 3.45, "FY27e": 3.65, "FY28e": 3.90},
        "payout_target": 0.65,
        "fcf_cover": 1.3,
        "net_debt_ebitda": 1.8,
        "scenarios": {
            "bear": {
                "FY26e": 3.30, "FY27e": 3.40, "FY28e": 3.50,
                "rationale": "Volume/FX pressure + restructuring charges keep DPS flat",
                "breakdown": {"Interim": 1.50, "Final": 1.80, "Total": 3.30, "note": "Maintain but no growth"}
            },
            "base": {
                "FY26e": 3.45, "FY27e": 3.65, "FY28e": 3.90,
                "rationale": "H1 OG 3.6%, guidance confirmed 3-4%; progressive DPS intact",
                "breakdown": {"Interim": 1.55, "Final": 1.90, "Total": 3.45, "note": "Standard split ~45/55"}
            },
            "bull": {
                "FY26e": 3.60, "FY27e": 3.90, "FY28e": 4.30,
                "rationale": "Stronger RIG + cost savings → modest payout lift",
                "breakdown": {"Interim": 1.60, "Final": 2.00, "Total": 3.60, "note": "Possible higher final"}
            },
        },
        "calendar_notes": "Interim typically Aug/Sep, final Apr/May of following year. Calendar mixes two FYs.",
        "risks": ["Commodity costs", "FX", "Infant formula recall residual", "Restructuring charges"],
        "upside_triggers": ["H2 margin acceleration", "Buyback increase"],
        "news_log": [
            {"date": "2026-07-23", "source": "H1 Results", "text": "H1 sales CHF 43.1bn, OG 3.6% (pricing 2.1%, RIG 1.5%). UTOP margin pressured by restructuring (CHF 0.8bn) and one-offs. Guidance confirmed: OG 3-4%, UTOP margin up vs 2025, FCF > CHF 9bn. Blue Bottle divested.", "impact": "base (guidance intact, one-offs noted)", "category": "Results"},
        ],
        "transcript_insights": {
            "event": "H1 2026 Earnings Call",
            "date": "2026-07-23",
            "source": "Company / Investing.com / MarketScreener transcript",
            "key_points": [
                "CEO: execution improving, RIG accelerating; target consistent delivery and RIG ≥2%.",
                "Guidance tightened to OG 3-4% (from 'around 3% up to 4%'); UTOP margin still expected to improve vs 2025; H2 margin broadly similar to H1.",
                "FCF expected > CHF 9bn; cost savings slightly ahead of plan.",
                "Restructuring and write-downs temporary; underlying trajectory supports progressive DPS.",
                "Portfolio actions (Waters partnership, Blue Bottle disposal) framed as focus-to-win, not capital-return change.",
            ],
            "dps_relevant_quotes": [
                "We now expect organic growth to be in the range of 3%-4%.",
                "Free cash flow is expected to be above CHF 9 billion.",
            ],
            "impact_on_scenarios": "Base case intact; one-offs do not change progressive DPS path.",
        },
    },
    "SHEL.L": {
        "name": "Shell",
        "isin": "GB00BP6MXD84",
        "country": "GB",
        "sector": "Energy",
        "fy_end": "12-31",
        "currency": "USD",
        "policy": "Quarterly (progressive ~4% p.a.)",
        "policy_flag": None,
        "shares_m": 6200.0,
        "last_reported": "Q2'26 (30 Jul)",
        "reported_eps_ytd": 2.94,
        "eps": {"FY25a": 3.40, "FY26e": 3.80, "FY27e": 3.60, "FY28e": 3.70},
        "dps_hist": {"FY23": 1.29, "FY24": 1.38, "FY25": 1.45},
        "consensus_dps": {"FY26e": 1.56, "FY27e": 1.62, "FY28e": 1.70},
        "payout_target": 0.40,
        "fcf_cover": 2.8,
        "net_debt_ebitda": 0.5,
        "scenarios": {
            "bear": {
                "FY26e": 1.48, "FY27e": 1.40, "FY28e": 1.30,
                "rationale": "Oil soft + higher capex/ARC → freeze after current level",
                "breakdown": {"Q1": 0.37, "Q2": 0.37, "Q3": 0.37, "Q4": 0.37, "Total": 1.48, "note": "Hold quarterly at ~$0.37"}
            },
            "base": {
                "FY26e": 1.56, "FY27e": 1.62, "FY28e": 1.70,
                "rationale": "Q2 strong ($9.8bn adj earnings), progressive 4%, $3bn+ buybacks continued",
                "breakdown": {"Q1": 0.3906, "Q2": 0.3906, "Q3": 0.39, "Q4": 0.39, "Total": 1.56, "note": "Current quarterly $0.3906; +~4% path"}
            },
            "bull": {
                "FY26e": 1.70, "FY27e": 1.85, "FY28e": 2.00,
                "rationale": "Strong CFFO + higher distribution ratio from excess FCF",
                "breakdown": {"Q1": 0.39, "Q2": 0.39, "Q3": 0.42, "Q4": 0.50, "Total": 1.70, "note": "Possible step-up in H2"}
            },
        },
        "calendar_notes": "Quarterly: payments lag ~1 quarter. Calendar DPS ≈ ¾ current FY + ¼ prior FY.",
        "risks": ["Oil/gas price", "Middle East disruptions", "Energy transition"],
        "upside_triggers": ["Buyback increase beyond $3bn", "Faster DPS growth"],
        "news_log": [
            {"date": "2026-07-30", "source": "Q2 Results", "text": "Adj earnings $9.8bn, CFFO $21.4bn. DPS $0.3906. New $3bn buyback (+$1.2bn residual) announced. Net debt down. ARC acquisition progressing. 19th consecutive ≥$3bn buyback quarter.", "impact": "base+ / capital return strong", "category": "Results"},
        ],
        "transcript_insights": {
            "event": "Q2 2026 Results Call",
            "date": "2026-07-30",
            "source": "Company / Seeking Alpha / Motley Fool transcript",
            "key_points": [
                "Very strong operational performance; adj earnings $9.8bn, CFFO $21.4bn despite Middle East disruptions.",
                "DPS held at $0.3906 (progressive); 19th consecutive quarter of ≥$3bn buyback announcement.",
                "New $3bn buyback + $1.2bn residual from prior programme; net debt reduced.",
                "Cash capex outlook $24-26bn unchanged (includes ARC); distribution policy 40-50% of CFFO through the cycle reiterated.",
                "Focus on controllable factors (asset performance, portfolio health) rather than price volatility.",
            ],
            "dps_relevant_quotes": [
                "Today, we commence another $3 billion of share buybacks, in line with our 40-50% of CFFO through the cycle distribution policy.",
                "Progressive Dividend 4% annual increase.",
            ],
            "impact_on_scenarios": "Strong support for base case; capital return flexibility remains high.",
        },
    },
    "SAN.MC": {
        "name": "Banco Santander",
        "isin": "ES0113900J37",
        "country": "ES",
        "sector": "Banks",
        "fy_end": "12-31",
        "currency": "EUR",
        "policy": "Semi-annual (ordinary ~50% of underlying, split cash/buyback)",
        "policy_flag": "Watch: excess capital distributions / higher buybacks vs cash DPS",
        "shares_m": 15500.0,
        "last_reported": "H1'26 (22 Jul)",
        "reported_eps_ytd": 0.47,
        "eps": {"FY25a": 0.75, "FY26e": 0.90, "FY27e": 0.98, "FY28e": 1.05},
        "dps_hist": {"FY23": 0.195, "FY24": 0.21, "FY25": 0.24},
        "consensus_dps": {"FY26e": 0.30, "FY27e": 0.34, "FY28e": 0.38},
        "payout_target": 0.50,
        "fcf_cover": None,
        "net_debt_ebitda": None,
        "scenarios": {
            "bear": {
                "FY26e": 0.26, "FY27e": 0.28, "FY28e": 0.30,
                "rationale": "Higher CoR / slower growth → cash DPS grows slowly, more buybacks",
                "breakdown": {"Interim": 0.12, "Final": 0.14, "Total": 0.26, "note": "Cash component only; buybacks extra"}
            },
            "base": {
                "FY26e": 0.30, "FY27e": 0.34, "FY28e": 0.38,
                "rationale": "H1 underlying profit +15% to €7.3bn, CET1 14.0%, on track for ≥€10bn buybacks 25-26",
                "breakdown": {"Interim": 0.14, "Final": 0.16, "Total": 0.30, "note": "Ordinary policy ~50% underlying, ~even cash/buyback"}
            },
            "bull": {
                "FY26e": 0.38, "FY27e": 0.45, "FY28e": 0.55,
                "rationale": "Excess capital special distributions + cash payout raised",
                "breakdown": {"Interim": 0.16, "Final": 0.22, "Total": 0.38, "note": "Possible special on top of ordinary"}
            },
        },
        "calendar_notes": "Interim ~Nov, final ~May. Buybacks are not DPS but reduce share count / support EPS.",
        "risks": ["LatAm FX/politics", "NII sensitivity", "Regulation"],
        "upside_triggers": ["CET1 well above target → special / higher cash DPS"],
        "news_log": [
            {"date": "2026-07-22", "source": "H1 Results", "text": "Underlying profit €7.3bn (+15%), RoTE 15.6%, CET1 14.0%. On track for ≥€10bn buybacks 2025-26 (c.€9bn already delivered/approved). Ordinary policy ~50% of underlying (cash + buybacks). Poland disposal capital also returned.", "impact": "bullish capital return / base DPS", "category": "Results"},
        ],
        "transcript_insights": {
            "event": "H1 2026 Earnings Call",
            "date": "2026-07-22",
            "source": "Company presentation + Motley Fool / MarketScreener transcript",
            "key_points": [
                "Record H1 underlying profit €7.3bn (+15%), RoTE 15.6%, CET1 14.0%.",
                "Ordinary shareholder remuneration ~50% of underlying (cash dividends + buybacks); on track for ≥€10bn buybacks 2025-26.",
                "c.€9bn of the buyback commitment already delivered or approved; Poland disposal capital also returned.",
                "Management reiterated disciplined capital allocation and high-teen shareholder value creation.",
                "No signal of change to the cash/buyback mix or introduction of specials beyond the stated plan.",
            ],
            "dps_relevant_quotes": [
                "the bank will have delivered c.€9 billion towards its commitment to distribute at least €10 billion through share buybacks for 2025 and 2026.",
                "ordinary shareholder remuneration policy for 2026 to 2028 results that entails distributing approximately 50% of the Group’s underlying profit.",
            ],
            "impact_on_scenarios": "Supports base DPS + strong total yield via buybacks; policy flag for excess capital remains relevant.",
        },
    },
    "AIR.PA": {
        "name": "Airbus",
        "isin": "NL0000235190",
        "country": "FR/NL",
        "sector": "Industrials",
        "fy_end": "12-31",
        "currency": "EUR",
        "policy": "Annual (final)",
        "policy_flag": None,
        "shares_m": 790.0,
        "last_reported": "H1'26 (29 Jul)",
        "reported_eps_ytd": 2.84,
        "eps": {"FY25a": 5.80, "FY26e": 6.80, "FY27e": 8.20, "FY28e": 9.80},
        "dps_hist": {"FY23": 1.80, "FY24": 2.00, "FY25": 2.20},
        "consensus_dps": {"FY26e": 2.50, "FY27e": 2.90, "FY28e": 3.40},
        "payout_target": 0.35,
        "fcf_cover": 1.4,
        "net_debt_ebitda": 0.3,
        "scenarios": {
            "bear": {
                "FY26e": 2.20, "FY27e": 2.40, "FY28e": 2.60,
                "rationale": "Delivery delays / supply chain → weaker FCF, conservative payout",
                "breakdown": {"Final only": 2.20, "Total": 2.20, "note": "Paid following spring"}
            },
            "base": {
                "FY26e": 2.50, "FY27e": 2.90, "FY28e": 3.40,
                "rationale": "H1 351 deliveries, guidance unchanged (~870 a/c, EBIT adj ~€7.5bn, FCF ~€4.5bn). Progressive",
                "breakdown": {"Final only": 2.50, "Total": 2.50, "note": "Standard annual final"}
            },
            "bull": {
                "FY26e": 2.90, "FY27e": 3.60, "FY28e": 4.50,
                "rationale": "Ramp success + higher FCF conversion → accelerated DPS growth",
                "breakdown": {"Final only": 2.90, "Total": 2.90, "note": "Possible special if FCF overshoots"}
            },
        },
        "calendar_notes": "Annual final paid in following calendar year → CY DPS ≈ prior FY DPS.",
        "risks": ["Supply chain (engines)", "Working-capital drag from ramp", "Geopolitics"],
        "upside_triggers": ["Delivery guidance raise", "FCF beat"],
        "news_log": [
            {"date": "2026-07-29", "source": "H1 Results", "text": "351 commercial aircraft delivered (H1). Revenues €33.2bn, EBIT adj €2.7bn, FCF before customer fin. –€1.2bn (inventory build). Guidance unchanged: ~870 deliveries, EBIT adj ~€7.5bn, FCF ~€4.5bn.", "impact": "base (guidance held)", "category": "Results"},
        ],
        "transcript_insights": {
            "event": "H1 2026 Results",
            "date": "2026-07-29",
            "source": "Company press release + presentation",
            "key_points": [
                "351 commercial aircraft delivered in H1; guidance unchanged at ~870 for full year.",
                "EBIT Adjusted €2.7bn; FCF before customer financing –€1.2bn due to planned inventory build for ramp.",
                "Full-year targets reiterated: EBIT adj ~€7.5bn, FCF ~€4.5bn (before M&A, including current tariffs).",
                "No explicit commentary on dividend policy change; progressive annual final remains the framework.",
                "Working-capital drag is timing-related to the production ramp, not a structural FCF concern for DPS.",
            ],
            "dps_relevant_quotes": [
                "The Company targets to achieve in 2026: Around 870 commercial aircraft deliveries; EBIT Adjusted of around €7.5 billion; Free Cash Flow before Customer Financing of around €4.5 billion.",
            ],
            "impact_on_scenarios": "Base case held; FCF timing does not alter expected progressive DPS path.",
        },
    },
}

# Relative paths so the app works both locally and on Streamlit Community Cloud
_APP_DIR = Path(__file__).parent
DATA_PATH = _APP_DIR / "user_data.json"
ALERTS_PATH = _APP_DIR / "daily_alerts.json"

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
        base["news_log"] = user["news_log"] + base.get("news_log", [])
    if "policy_flag" in user:
        base["policy_flag"] = user["policy_flag"]
    if "eps" in user:
        base["eps"].update(user["eps"])
    return base

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
        },
        "summary": [],
    }

    alerts["categories"]["Results"].extend([
        {"ticker": "ASML.AS", "date": "2026-07-15", "headline": "Q2 beat + FY26 sales guidance raised to €43-45bn", "impact": "EPS up → support higher DPS path", "action": "Review base/bull; interim already at €1.88"},
        {"ticker": "NESN.SW", "date": "2026-07-23", "headline": "H1 OG 3.6%, guidance confirmed, restructuring charges noted", "impact": "Base intact; one-offs temporary", "action": "No DPS change expected"},
        {"ticker": "SHEL.L", "date": "2026-07-30", "headline": "Q2 adj earnings $9.8bn, CFFO $21.4bn, DPS held progressive", "impact": "Supports base + capital return", "action": "Monitor Q3 buyback execution"},
        {"ticker": "SAN.MC", "date": "2026-07-22", "headline": "H1 underlying €7.3bn (+15%), CET1 14%, buyback path on track", "impact": "Capital return strong; cash DPS progressive", "action": "Watch for special distributions"},
        {"ticker": "AIR.PA", "date": "2026-07-29", "headline": "H1 351 deliveries, guidance unchanged, FCF negative on inventory", "impact": "Base case held; FCF timing risk", "action": "No immediate DPS revision"},
    ])

    alerts["categories"]["Capital Return"].extend([
        {"ticker": "ASML.AS", "date": "2026-08-05", "headline": "Interim €1.88 paid; 2026-28 buyback programme active", "impact": "Positive for total yield", "action": "Update calendar breakdown"},
        {"ticker": "SHEL.L", "date": "2026-07-30", "headline": "New $3bn buyback (+$1.2bn residual) – 19th consecutive ≥$3bn quarter", "impact": "Strong FCF distribution", "action": "EPS accretion support"},
        {"ticker": "SAN.MC", "date": "2026-07-22", "headline": "c.€9bn of ≥€10bn 2025-26 buyback commitment already delivered/approved", "impact": "Excess capital returning", "action": "Bull case for total shareholder yield"},
    ])

    alerts["categories"]["One-offs / Corporate Actions"].extend([
        {"ticker": "NESN.SW", "date": "2026-07-23", "headline": "Restructuring + write-downs + Blue Bottle disposal", "impact": "Temporary EPS noise; underlying intact", "action": "Strip one-offs for DPS sustainability view"},
        {"ticker": "SHEL.L", "date": "2026-07-30", "headline": "ARC Resources acquisition progressing (completion expected Q3)", "impact": "Capex/production growth; temporary buyback pause resolved", "action": "Monitor integration & distribution policy"},
    ])

    alerts["categories"]["Policy / Payout"].extend([
        {"ticker": "ASML.AS", "date": "2026-07-15", "headline": "Continued multi-interim structure + progressive intent (from earnings call)", "impact": "Pattern already shifted from pure annual", "action": "Calendar-year modelling must use interims"},
        {"ticker": "SAN.MC", "date": "2026-07-22", "headline": "Ordinary ~50% underlying (cash + buybacks); excess capital at period-end possible (call commentary)", "impact": "Policy flexible between cash DPS and buybacks", "action": "Flag for potential special"},
    ])

    alerts["categories"]["Results"].append(
        {"ticker": "ASML.AS", "date": "2026-07-15", "headline": "Transcript: Interim €1.88 confirmed + €1.1bn buybacks; guidance raise supports cash returns", "impact": "Direct support for progressive DPS path", "action": "See Earnings Call Insights tab"}
    )
    alerts["categories"]["Capital Return"].append(
        {"ticker": "SHEL.L", "date": "2026-07-30", "headline": "Transcript: 40-50% of CFFO distribution policy reiterated; progressive 4% DPS language", "impact": "Policy continuity + buyback strength", "action": "See Earnings Call Insights tab"}
    )

    alerts["categories"]["Consensus / Research"].append(
        {"ticker": "Universe", "date": today, "headline": "Post-results consensus still digesting ASML guidance raise and Shell/Santander capital returns", "impact": "Mild upward bias to FY26 DPS for quality compounders", "action": "Re-pull IBES/FactSet when available"}
    )

    alerts["categories"]["Market Chatter"].append(
        {"ticker": "ASML.AS", "date": "2026-08-10", "headline": "Sell-side positive on AI demand resilience despite China noise", "impact": "Supports bull case", "action": "Watch export-control headlines"}
    )

    alerts["summary"] = [
        f"{today}: 5 official results packages in last 30 days processed for sample universe.",
        "Highest near-term DPS relevance: ASML interim paid + guidance raise; Shell/Santander capital returns strong.",
        "No active dividend-cut risk flags in sample set.",
        "Action: review ASML & SAN breakdowns; consider mild upward bias to base cases where guidance raised.",
    ]

    save_json(ALERTS_PATH, alerts)
    return alerts

def load_or_generate_alerts():
    alerts = load_json(ALERTS_PATH)
    if not alerts or alerts.get("scan_date") != date.today().isoformat():
        alerts = generate_daily_alerts()
    return alerts

# ----------------------
# UI
# ----------------------
st.set_page_config(page_title="STOXX 600 DPS Scenario Tracker", layout="wide", page_icon="📈")

st.title("📈 STOXX 600 DPS Scenario Tracker")
st.caption("Bear / Base / Bull with interim·final·quarterly breakdowns · Earnings-call transcript insights · Daily automated intelligence & categorized alerts · Prototype")

with st.sidebar:
    st.header("Universe")
    tickers = list(SAMPLE_UNIVERSE.keys())
    names = [f"{t} – {SAMPLE_UNIVERSE[t]['name']}" for t in tickers]
    choice = st.selectbox("Select stock", names, index=0)
    ticker = choice.split(" – ")[0]

    st.markdown("---")
    stock = get_stock_data(ticker)
    if stock.get("policy_flag"):
        st.warning(f"⚠️ Policy flag: {stock['policy_flag']}")
    else:
        st.success("No active policy-change flag")
    st.markdown(f"**Policy:** {stock.get('policy')}")
    st.markdown(f"**FCF cover:** {stock.get('fcf_cover')}")
    st.markdown(f"**Net debt/EBITDA:** {stock.get('net_debt_ebitda')}")

    st.markdown("---")
    if st.button("🔄 Run / Refresh Daily Scan", type="primary"):
        generate_daily_alerts()
        st.success("Daily intelligence refreshed")
        st.rerun()

    st.info("Prototype uses curated official results + structure for live news APIs / X / LLM.")

stock = get_stock_data(ticker)
col1, col2, col3, col4 = st.columns([2.2, 1, 1, 1])
with col1:
    st.subheader(f"{stock['name']} ({ticker})")
    st.markdown(f"{stock['sector']} · {stock['country']} · FY {stock['fy_end']} · {stock['currency']}")
with col2:
    st.metric("Cons. DPS FY26e", f"{stock['consensus_dps']['FY26e']:.2f}")
with col3:
    st.metric("Last reported", stock.get("last_reported", "–"))
with col4:
    st.metric("Policy pattern", stock.get("policy", "–")[:18] + "…")

tab_alerts, tab_tx, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚨 Daily Alerts",
    "🎙️ Earnings Call Insights",
    "📊 Scenarios + Breakdown",
    "📅 Calendar vs FY",
    "🔄 Results & EPS Adjust",
    "📰 News / Rumours / Policy",
    "📋 Universe Snapshot",
])

with tab_alerts:
    alerts = load_or_generate_alerts()
    st.markdown(f"### Morning Intelligence · Scan date **{alerts.get('scan_date', '–')}**")
    st.caption(f"Generated at {alerts.get('generated_at', '–')}")

    for s in alerts.get("summary", []):
        st.markdown(f"- {s}")

    st.markdown("---")
    cats = alerts.get("categories", {})
    for cat, items in cats.items():
        if not items:
            continue
        with st.expander(f"**{cat}** ({len(items)})", expanded=(cat in ("Results", "Capital Return"))):
            for it in items:
                st.markdown(f"**{it.get('ticker', '')}** · {it.get('date', '')}")
                st.markdown(f"{it.get('headline', '')}")
                st.caption(f"Impact: {it.get('impact', '')}  |  Suggested action: {it.get('action', '')}")
                st.markdown("")

    st.info(
        "Production automation path: daily cron → fetch company PR / results calendars / NewsAPI / Finnhub / X semantic search → "
        "LLM classifies into the 6 categories above → writes alerts + optional auto-suggested scenario deltas → "
        "Slack / email / Teams notification per category. This UI already consumes the same JSON schema."
    )

with tab_tx:
    st.markdown("### Earnings Call Transcript Insights (capital-return focused)")
    st.caption(
        "Key management comments extracted from the latest results call / investor call. "
        "In production these are pulled via transcript APIs and auto-summarised for DPS / payout / FCF / buyback / policy signals."
    )

    ti = stock.get("transcript_insights")
    if not ti:
        st.warning("No transcript insights loaded for this name yet.")
    else:
        st.markdown(f"**Event:** {ti.get('event')} · **Date:** {ti.get('date')} · **Source:** {ti.get('source')}")
        st.markdown(f"**Impact on scenarios:** {ti.get('impact_on_scenarios', '–')}")

        st.markdown("#### Key points")
        for pt in ti.get("key_points", []):
            st.markdown(f"- {pt}")

        if ti.get("dps_relevant_quotes"):
            st.markdown("#### DPS / capital-return relevant quotes")
            for q in ti["dps_relevant_quotes"]:
                st.markdown(f"> {q}")

        st.markdown("---")
        st.markdown("#### How this feeds the model")
        st.markdown(
            "- Quotes and key points are automatically eligible for the Daily Alerts (Results / Capital Return / Policy categories).\n"
            "- Material guidance or policy language can trigger a suggested scenario revision (you approve).\n"
            "- Payment-pattern comments (interim vs final, quarterly step-up) update the breakdown view."
        )

with tab1:
    st.markdown("### Bear / Base / Bull DPS (FY) + Payment Pattern Breakdown")
    scen = stock["scenarios"]

    df_scen = pd.DataFrame({
        "Case": ["Bear", "Base", "Bull"],
        "FY26e": [scen["bear"]["FY26e"], scen["base"]["FY26e"], scen["bull"]["FY26e"]],
        "FY27e": [scen["bear"]["FY27e"], scen["base"]["FY27e"], scen["bull"]["FY27e"]],
        "FY28e": [scen["bear"]["FY28e"], scen["base"]["FY28e"], scen["bull"]["FY28e"]],
        "Rationale": [scen["bear"]["rationale"], scen["base"]["rationale"], scen["bull"]["rationale"]],
    })
    st.dataframe(df_scen, use_container_width=True, hide_index=True)

    st.markdown("#### Pattern breakdown (interim / final / quarterly components)")
    for case, label, color in [("bear", "Bear", "red"), ("base", "Base", "blue"), ("bull", "Bull", "green")]:
        bd = scen[case].get("breakdown", {})
        st.markdown(f"**{label}** — Total FY26e: **{scen[case]['FY26e']:.3f}** {stock['currency']}")
        cols = st.columns(len([k for k in bd if k not in ("note", "Total")]) + 1)
        i = 0
        for k, v in bd.items():
            if k in ("note", "Total"):
                continue
            cols[i].metric(k, f"{v:.3f}" if isinstance(v, (int, float)) else v)
            i += 1
        if "note" in bd:
            st.caption(bd["note"])
        st.markdown("")

    fig = go.Figure()
    years = ["FY26e", "FY27e", "FY28e"]
    for case, color in [("bear", "#ef4444"), ("base", "#3b82f6"), ("bull", "#22c55e")]:
        fig.add_trace(go.Scatter(
            x=years, y=[scen[case][y] for y in years],
            mode="lines+markers", name=case.capitalize(),
            line=dict(color=color, width=3), marker=dict(size=10),
        ))
    fig.add_trace(go.Scatter(
        x=years, y=[stock["consensus_dps"].get(y) for y in years],
        mode="markers", name="Consensus",
        marker=dict(symbol="diamond", size=12, color="black"),
    ))
    fig.update_layout(title="DPS Scenario Paths", yaxis_title=f"DPS ({stock['currency']})",
                      height=380, legend=dict(orientation="h"), template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Historical DPS**")
    st.write(stock.get("dps_hist", {}))

with tab2:
    st.markdown("### Calendar-year DPS (dividend-futures relevant)")
    st.markdown(
        "Fiscal DPS is the accounting/guidance number. Dividend futures settle on **calendar-year** gross ordinary dividends paid. "
        "A shift in payment pattern (annual → interim/final or quarterly) changes the lag even if the full-year total is unchanged."
    )
    cal = compute_calendar_dps(stock)
    c1, c2, c3 = st.columns(3)
    c1.metric("Bear CY (illustrative)", f"{cal['bear']:.3f}")
    c2.metric("Base CY", f"{cal['base']:.3f}")
    c3.metric("Bull CY", f"{cal['bull']:.3f}")
    st.caption(cal["note"])
    st.markdown(f"**Company note:** {stock.get('calendar_notes', '')}")

    if stock.get("policy_flag"):
        st.warning(
            f"⚠️ Active policy flag: **{stock['policy_flag']}**. "
            "Model both the FY path and the exact payment schedule for futures positioning."
        )

with tab3:
    st.markdown("### Adjust from reported results & sell-side updates")
    st.markdown("After a print, lock hard data and re-scale remaining year + outer years. Overlay sell-side revisions.")

    with st.form("eps_adjust"):
        st.write("Current EPS estimates (edit → rescale DPS scenarios + breakdowns)")
        e26 = st.number_input("FY26e EPS", value=float(stock["eps"].get("FY26e", 0)), format="%.3f")
        e27 = st.number_input("FY27e EPS", value=float(stock["eps"].get("FY27e", 0)), format="%.3f")
        e28 = st.number_input("FY28e EPS", value=float(stock["eps"].get("FY28e", 0)), format="%.3f")
        payout_mult = st.slider("Payout multiplier (1.0 = keep implied)", 0.7, 1.4, 1.0, 0.05)
        note = st.text_input("Adjustment note (e.g. 'H1 beat + guidance raise')")
        submitted = st.form_submit_button("Apply EPS revision → rescale DPS + breakdowns")

        if submitted:
            new_eps = {"FY26e": e26, "FY27e": e27, "FY28e": e28}
            updated = adjust_scenarios_from_eps(stock, new_eps, payout_mult)
            user = load_json(DATA_PATH)
            user[ticker] = user.get(ticker, {})
            user[ticker]["eps"] = updated["eps"]
            user[ticker]["scenarios"] = updated["scenarios"]
            if note:
                user[ticker].setdefault("news_log", [])
                user[ticker]["news_log"].insert(0, {
                    "date": str(date.today()), "source": "User / Results",
                    "text": note, "impact": f"EPS adj ×{payout_mult:.2f}", "category": "Results",
                })
            save_json(DATA_PATH, user)
            st.success("Scenarios + breakdowns updated.")
            st.rerun()

with tab4:
    st.markdown("### News, market chatter, company comments & policy flags")
    for item in stock.get("news_log", [])[:12]:
        st.markdown(f"**{item['date']}** · *{item['source']}* · `{item.get('category', item.get('impact', ''))}`")
        st.write(item["text"])
        st.markdown("---")

    with st.form("add_news"):
        ndate = st.date_input("Date", value=date.today())
        nsource = st.selectbox("Source", ["Company PR", "Results", "Sell-side", "Rumour / X / press", "Other"])
        ncat = st.selectbox("Category", ["Results", "Capital Return", "Policy / Payout", "One-offs / Corporate Actions", "Consensus / Research", "Market Chatter"])
        ntext = st.text_area("Comment / extract")
        nimpact = st.selectbox("Suggested impact", ["neutral", "base", "bullish bias", "bearish bias", "policy flag"])
        nflag = st.text_input("Optional new policy_flag (blank = keep)")
        add = st.form_submit_button("Add to log & optionally set flag")

        if add and ntext:
            user = load_json(DATA_PATH)
            user[ticker] = user.get(ticker, {})
            user[ticker].setdefault("news_log", [])
            user[ticker]["news_log"].insert(0, {
                "date": str(ndate), "source": nsource, "text": ntext,
                "impact": nimpact, "category": ncat,
            })
            if nflag:
                user[ticker]["policy_flag"] = nflag
            save_json(DATA_PATH, user)
            st.success("Logged.")
            st.rerun()

with tab5:
    st.markdown("### Sample universe snapshot")
    rows = []
    for t, s in SAMPLE_UNIVERSE.items():
        rows.append({
            "Ticker": t, "Name": s["name"], "Sector": s["sector"],
            "Policy": s["policy"][:28] + ("…" if len(s["policy"]) > 28 else ""),
            "Flag": s.get("policy_flag") or "–",
            "DPS FY26e Base": s["scenarios"]["base"]["FY26e"],
            "Range FY26e": f"{s['scenarios']['bear']['FY26e']:.2f}–{s['scenarios']['bull']['FY26e']:.2f}",
            "FY27e Base": s["scenarios"]["base"]["FY27e"],
            "FY28e Base": s["scenarios"]["base"]["FY28e"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown("---")
st.caption(f"Prototype · illustrative data enriched with official mid-2026 results · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
