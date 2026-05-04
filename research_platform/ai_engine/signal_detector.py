"""
ai_engine/signal_detector.py
──────────────────────────────
Layer 6 — Hybrid Signal / Event Detection.

Architecture (from the document):
  keyword filter (deterministic) → LLM interprets only tagged content
  → forced structured output schema

This is the "Two Brains" principle in action:
  Brain 1 (this file): keyword matching is deterministic — no LLM involved.
    Finds candidate signals fast and cheaply.
  Brain 2 (llm_layer.py): only runs LLM on the pre-tagged candidates.
    Never on raw text. Forces structured JSON output.

Why hybrid?
  Pure LLM detection is non-deterministic — same news article can produce
  different signals on different runs. Keyword filter fixes this: the same
  article always produces the same candidates. LLM only decides severity
  and factor impact, which has a much smaller variance surface.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from loguru import logger

FRAMEWORKS_DIR = Path(__file__).parent / "frameworks"

# ── Sector detection ──────────────────────────────────────────────────────────

SECTOR_KEYWORDS: dict[str, list[str]] = {
    "petroleum":    ["refinery", "crude", "petroleum", "oil", "gas", "bpcl", "iocl", "hpcl", "ongc", "reliance"],
    "banking":      ["bank", "nbfc", "lending", "deposit", "loan", "npa", "nim", "hdfc", "icici", "sbi", "axis", "kotak"],
    "fmcg":         ["consumer", "fmcg", "fmcg", "hul", "itc", "dabur", "marico", "nestle", "britannia", "godrej"],
    "pharma":       ["pharma", "drug", "medicine", "api", "fda", "anda", "cipla", "sunpharma", "drreddy", "lupin"],
    "it":           ["software", "it services", "tcs", "infosys", "wipro", "hcl", "tech mahindra", "deal", "attrition"],
    "real_estate":  ["realty", "real estate", "housing", "project", "pre-sales", "bookings", "dlf", "oberoi", "godrej properties"],
    "auto":         ["automobile", "vehicle", "auto", "tata motors", "maruti", "m&m", "bajaj auto", "hero", "tvs"],
}


def detect_sector(text: str, ticker: Optional[str] = None) -> str:
    """Return the most likely sector for a piece of text or ticker."""
    text_lower = (text + " " + (ticker or "")).lower()
    scores: dict[str, int] = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        scores[sector] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=lambda s: scores[s])
    return best if scores[best] > 0 else "universal"


# ── Framework loader ──────────────────────────────────────────────────────────

_framework_cache: dict[str, dict] = {}


def _load_framework(sector: str) -> dict:
    """Load sector signals from frameworks/<sector>/signals.json."""
    if sector in _framework_cache:
        return _framework_cache[sector]

    # Load universal signals always
    universal_path = FRAMEWORKS_DIR / "universal.json"
    universal = {}
    if universal_path.exists():
        universal = json.loads(universal_path.read_text())

    # Load sector-specific signals if not universal
    sector_signals: list[dict] = []
    if sector != "universal":
        sector_path = FRAMEWORKS_DIR / sector / "signals.json"
        if sector_path.exists():
            sector_data = json.loads(sector_path.read_text())
            sector_signals = sector_data.get("signals", [])
            _framework_cache[sector] = {
                "universal": universal.get("signals", []),
                "sector": sector_signals,
                "meta": {k: v for k, v in sector_data.items() if not k.startswith("signal")},
            }
        else:
            logger.warning(f"[signal_detector] No framework for sector: {sector}")
            _framework_cache[sector] = {"universal": universal.get("signals", []), "sector": [], "meta": {}}
    else:
        _framework_cache[sector] = {"universal": universal.get("signals", []), "sector": [], "meta": {}}

    return _framework_cache[sector]


# ── Core detection ────────────────────────────────────────────────────────────

class DetectedSignal:
    """One detected signal from a piece of text."""

    def __init__(
        self,
        signal_id: str,
        signal_name: str,
        level: str,           # "universal" | "sector"
        sector: str,
        matched_keywords: list[str],
        source_text: str,
        source_name: str,
        factors: list[str],
        transmission: str,
        severity: str = "medium",    # low | medium | high — keyword-derived default
        direction: Optional[str] = None,  # positive | negative | neutral
    ) -> None:
        self.signal_id       = signal_id
        self.signal_name     = signal_name
        self.level           = level
        self.sector          = sector
        self.matched_keywords = matched_keywords
        self.source_text     = source_text[:500]
        self.source_name     = source_name
        self.factors         = factors
        self.transmission    = transmission
        self.severity        = severity
        self.direction       = direction

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id":        self.signal_id,
            "signal_name":      self.signal_name,
            "level":            self.level,
            "sector":           self.sector,
            "matched_keywords": self.matched_keywords,
            "source_text":      self.source_text,
            "source_name":      self.source_name,
            "factors":          self.factors,
            "transmission":     self.transmission,
            "severity":         self.severity,
            "direction":        self.direction,
        }

    def __repr__(self) -> str:
        return f"<Signal {self.signal_id} [{self.severity}] factors={self.factors}>"


def detect_signals(
    text: str,
    source_name: str,
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
) -> list[DetectedSignal]:
    """
    Phase 1: Keyword matching (deterministic).
    Returns a list of DetectedSignal objects ready for LLM interpretation.

    This function is the keyword filter. It tags content that MIGHT be
    a signal. The LLM layer (signal_detector_llm.py) then decides the
    exact severity and assumption impact for each tagged signal.
    """
    if not text.strip():
        return []

    detected_sector = sector or detect_sector(text, ticker)
    framework = _load_framework(detected_sector)
    text_lower = text.lower()

    results: list[DetectedSignal] = []

    # Check both universal and sector signals
    all_signal_defs = [
        ("universal", s) for s in framework.get("universal", [])
    ] + [
        (detected_sector, s) for s in framework.get("sector", [])
    ]

    for level, signal_def in all_signal_defs:
        keywords: list[str] = signal_def.get("keywords", [])
        matched = [kw for kw in keywords if kw.lower() in text_lower]

        if not matched:
            continue

        # Derive initial severity from keyword severity map if available
        severity = "medium"
        direction = None
        severity_map: dict[str, str] = signal_def.get("severity_map", {})
        for kw, sev_str in severity_map.items():
            if kw.lower() in text_lower:
                # Parse "positive_high" → direction="positive", severity="high"
                parts = sev_str.split("_")
                if len(parts) >= 2:
                    direction = parts[0]
                    severity = parts[1]
                elif parts[0] in ("high", "medium", "low"):
                    severity = parts[0]
                break

        results.append(DetectedSignal(
            signal_id=signal_def["id"],
            signal_name=signal_def["name"],
            level=level,
            sector=detected_sector,
            matched_keywords=matched,
            source_text=text,
            source_name=source_name,
            factors=signal_def.get("factors", []),
            transmission=signal_def.get("transmission", ""),
            severity=severity,
            direction=direction,
        ))

    if results:
        logger.info(
            f"[signal_detector] Detected {len(results)} signals in '{source_name}': "
            + ", ".join(s.signal_id for s in results)
        )

    return results


def scan_events_for_signals(
    events: list[dict[str, Any]],
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
) -> list[DetectedSignal]:
    """
    Scan a list of Event dicts (from DB or RSS) for signals.
    Each dict should have 'title' and optionally 'body', 'source'.
    """
    all_signals: list[DetectedSignal] = []
    for event in events:
        text = " ".join(filter(None, [
            event.get("title", ""),
            event.get("body", ""),
        ]))
        source_name = event.get("source", event.get("entity_type", "unknown"))
        signals = detect_signals(text, source_name, ticker=ticker, sector=sector)
        all_signals.extend(signals)
    return all_signals


def deduplicate_signals(signals: list[DetectedSignal]) -> list[DetectedSignal]:
    """Remove duplicate signal detections for the same signal_id."""
    seen: set[str] = set()
    unique: list[DetectedSignal] = []
    for s in signals:
        if s.signal_id not in seen:
            seen.add(s.signal_id)
            unique.append(s)
    return unique
