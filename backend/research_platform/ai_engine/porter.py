"""
ai_engine/porter.py
────────────────────
Porter's Five Forces generator ported from the company_research notebook.
Works from session data + sector framework files.

Returns Low / Medium / High rating with a 1-sentence rationale and
a FACT | ASSUMPTION | INTERPRETATION tag for each force.

Never fails — returns Medium / ASSUMPTION for all forces if data missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"

# Sector → default forces override table
# Values: (competitive_rivalry, supplier_power, buyer_power,
#           threat_of_substitutes, threat_of_new_entrants)
_SECTOR_DEFAULTS: dict[str, tuple[str, str, str, str, str]] = {
    "petroleum_energy": ("High",   "High",   "Medium", "Medium", "Low"),
    "banking_nbfc":     ("High",   "Low",    "Medium", "Medium", "Medium"),
    "fmcg_retail":      ("High",   "Medium", "High",   "Medium", "Medium"),
    "pharma":           ("Medium", "Medium", "Low",    "High",   "Low"),
    "it_tech":          ("High",   "Low",    "Medium", "High",   "Medium"),
    "real_estate":      ("Medium", "High",   "Medium", "Low",    "Low"),
    "auto":             ("High",   "High",   "Medium", "Medium", "Medium"),
}

_SUBSTITUTES_HIGH  = {"pharma", "it_tech"}
_SUBSTITUTES_LOW   = {"banking_nbfc", "real_estate"}
_ENTRANT_LOW_CAPEX = {"it_tech", "fmcg_retail"}
_SUPPLIER_HIGH     = {"petroleum_energy", "auto", "real_estate"}


def _load_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as exc:
        logger.debug(f"[porter] could not load {path}: {exc}")
    return None


def _get_peer_count(session: Any) -> int | None:
    """Try to read peer count from session sources or screener data."""
    try:
        sources = _load_json(session.sources_file)
        if isinstance(sources, list):
            screener = next(
                (s for s in sources if "screener" in (s.get("source_name") or "").lower()),
                None,
            )
            if screener and screener.get("records_returned", 0) > 0:
                return screener["records_returned"]
    except Exception:
        pass
    return None


def _safe_float(val: Any) -> float | None:
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


# ── Five force builders ───────────────────────────────────────────────────────

def _competitive_rivalry(
    sector: str,
    assumptions: dict[str, Any],
    sector_defaults: tuple[str, str, str, str, str] | None,
    peer_count: int | None,
) -> dict[str, str]:
    defaults = sector_defaults or ("Medium",) * 5
    base_rating = defaults[0]

    ebitda = _safe_float(assumptions.get("ebitda_margin"))
    sector_ebitda = _safe_float(
        _load_sector_defaults(sector).get("ebitda_margin_default") or
        _load_sector_defaults(sector).get("ebitda_margin")
    ) or 18.0

    if ebitda is not None and ebitda > sector_ebitda + 5:
        return {
            "rating":    "Medium",
            "rationale": f"Above-average EBITDA margin ({ebitda:.1f}%) suggests differentiated positioning that partially insulates from rivalry.",
            "tag":       "FACT",
        }

    if peer_count is not None:
        if peer_count > 10:
            return {
                "rating":    "High",
                "rationale": f"Large number of listed peers ({peer_count}) indicates a fragmented, competitive market.",
                "tag":       "FACT",
            }
        elif peer_count <= 3:
            return {
                "rating":    "Low",
                "rationale": f"Few listed peers ({peer_count}) — oligopolistic sector with limited direct rivalry.",
                "tag":       "FACT",
            }

    return {
        "rating":    base_rating,
        "rationale": f"Competitive intensity typical for {sector.replace('_', ' ')} sector based on sector framework.",
        "tag":       "ASSUMPTION",
    }


def _supplier_power(
    sector: str,
    sector_defaults: tuple[str, str, str, str, str] | None,
) -> dict[str, str]:
    defaults = sector_defaults or ("Medium",) * 5
    rating = defaults[1]
    if sector in _SUPPLIER_HIGH:
        return {
            "rating":    "High",
            "rationale": "Input costs (crude / raw materials / land) are globally priced and beyond company control.",
            "tag":       "INTERPRETATION",
        }
    return {
        "rating":    rating,
        "rationale": f"Supplier concentration in {sector.replace('_', ' ')} sector implies {rating.lower()} bargaining power.",
        "tag":       "ASSUMPTION",
    }


def _buyer_power(
    sector: str,
    assumptions: dict[str, Any],
    sector_defaults: tuple[str, str, str, str, str] | None,
) -> dict[str, str]:
    defaults = sector_defaults or ("Medium",) * 5
    rating = defaults[2]
    # If revenue is concentrated (implied by low peers / B2B sector)
    if sector in ("banking_nbfc", "pharma"):
        return {
            "rating":    "Low",
            "rationale": "Highly regulated / specialised products reduce buyer ability to switch or negotiate aggressively.",
            "tag":       "INTERPRETATION",
        }
    if sector == "fmcg_retail":
        return {
            "rating":    "High",
            "rationale": "Consumer goods face strong retailer and distributor bargaining power in modern trade.",
            "tag":       "INTERPRETATION",
        }
    return {
        "rating":    rating,
        "rationale": f"Buyer concentration in {sector.replace('_', ' ')} sector implies {rating.lower()} buyer power.",
        "tag":       "ASSUMPTION",
    }


def _threat_of_substitutes(
    sector: str,
    sector_defaults: tuple[str, str, str, str, str] | None,
) -> dict[str, str]:
    defaults = sector_defaults or ("Medium",) * 5
    if sector in _SUBSTITUTES_HIGH:
        return {
            "rating":    "High",
            "rationale": "Technology or therapy disruption presents a material substitution risk in this sector.",
            "tag":       "INTERPRETATION",
        }
    if sector in _SUBSTITUTES_LOW:
        return {
            "rating":    "Low",
            "rationale": "Structural need and regulatory moats make substitution unlikely in the medium term.",
            "tag":       "INTERPRETATION",
        }
    return {
        "rating":    defaults[3],
        "rationale": f"Substitution risk is {defaults[3].lower()} for {sector.replace('_', ' ')} based on sector analysis.",
        "tag":       "ASSUMPTION",
    }


def _threat_of_new_entrants(
    sector: str,
    assumptions: dict[str, Any],
    sector_defaults: tuple[str, str, str, str, str] | None,
) -> dict[str, str]:
    defaults = sector_defaults or ("Medium",) * 5
    capex_pct = _safe_float(assumptions.get("capex_pct_revenue"))

    if capex_pct is not None:
        if capex_pct > 15:
            return {
                "rating":    "Low",
                "rationale": f"High capex intensity ({capex_pct:.1f}% of revenue) creates significant capital barriers to entry.",
                "tag":       "FACT",
            }
        if capex_pct < 5 and sector in _ENTRANT_LOW_CAPEX:
            return {
                "rating":    "High",
                "rationale": f"Low capex ({capex_pct:.1f}% of revenue) and software-friendly sector make entry relatively easy.",
                "tag":       "FACT",
            }

    return {
        "rating":    defaults[4],
        "rationale": f"Entry barriers in {sector.replace('_', ' ')} are {defaults[4].lower()} based on regulatory and capital requirements.",
        "tag":       "ASSUMPTION",
    }


def _load_sector_defaults(sector: str) -> dict[str, Any]:
    folder_map = {
        "petroleum_energy": "petroleum",
        "banking_nbfc":     "banking",
        "fmcg_retail":      "fmcg",
        "it_tech":          "it",
        "pharma":           "pharma",
        "real_estate":      "real_estate",
        "auto":             "auto",
    }
    folder = folder_map.get(sector, sector)
    try:
        f = FRAMEWORKS_DIR / folder / "signals.json"
        if f.exists():
            return json.loads(f.read_text()).get("default_assumptions", {})
    except Exception:
        pass
    return {}


# ── Main public function ──────────────────────────────────────────────────────

_NEUTRAL: dict[str, dict] = {
    "competitive_rivalry":    {"rating": "Medium", "rationale": "Insufficient data.", "tag": "ASSUMPTION"},
    "supplier_power":         {"rating": "Medium", "rationale": "Insufficient data.", "tag": "ASSUMPTION"},
    "buyer_power":            {"rating": "Medium", "rationale": "Insufficient data.", "tag": "ASSUMPTION"},
    "threat_of_substitutes":  {"rating": "Medium", "rationale": "Insufficient data.", "tag": "ASSUMPTION"},
    "threat_of_new_entrants": {"rating": "Medium", "rationale": "Insufficient data.", "tag": "ASSUMPTION"},
}


def generate_porter(
    session: Any,            # ResearchSession
    sector:  str = "other",
) -> dict[str, dict]:
    """
    Generate Porter's Five Forces from session data + sector framework.
    Returns a dict with five force keys, each containing:
      rating    : Low | Medium | High
      rationale : one-sentence explanation
      tag       : FACT | ASSUMPTION | INTERPRETATION

    Never fails — returns Medium / ASSUMPTION defaults if data missing.

    Args:
        session: ResearchSession instance
        sector:  sector string

    Returns:
        dict of five forces
    """
    import copy
    result = copy.deepcopy(_NEUTRAL)

    try:
        assumptions: dict[str, Any] = {}
        try:
            assumptions = session.get_assumptions() or {}
        except Exception:
            pass

        sector_defaults = _SECTOR_DEFAULTS.get(sector)
        peer_count      = _get_peer_count(session)

        result["competitive_rivalry"]    = _competitive_rivalry(sector, assumptions, sector_defaults, peer_count)
        result["supplier_power"]         = _supplier_power(sector, sector_defaults)
        result["buyer_power"]            = _buyer_power(sector, assumptions, sector_defaults)
        result["threat_of_substitutes"]  = _threat_of_substitutes(sector, sector_defaults)
        result["threat_of_new_entrants"] = _threat_of_new_entrants(sector, assumptions, sector_defaults)

        logger.info(f"[porter] Five Forces generated for sector={sector}")

    except Exception as exc:
        logger.error(f"[porter] generate_porter failed: {exc}")

    return result
