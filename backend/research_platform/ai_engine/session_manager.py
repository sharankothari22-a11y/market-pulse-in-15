"""
ai_engine/session_manager.py
─────────────────────────────
Layer 2 — Research Session Manager.

FIXES applied vs previous version:
  - new_session() now accepts and stores: hypothesis, thesis, variant_view,
    price_target, catalyst — all required by Section 13 of the document
  - log_catalyst() / update_thesis() / update_variant_view() added
  - session_meta.json now includes all 4 equity research fields

Every company research session gets an isolated folder:
  sessions/<TICKER>_<YYYYMMDD>_<HHMMSS>/
    session_meta.json         — ticker, thesis, catalyst, variant_view, price_target
    sources.json              — every data source: URL/file/timestamp
    insights.json             — detected signals with source references
    assumptions.json          — CURRENT live assumptions (bridge to DCF engine)
    assumptions_history.json  — full version history of every change
    guardrail_log.json        — every guardrail breach
    hash_registry.json        — hash of every raw data pull
    llm_cache.json            — cached LLM outputs
    scenarios.json            — Bull / Base / Bear outputs + sensitivity table
    audit_log.json            — every command and update logged sequentially
    summary.md                — final auto-generated research report
    raw_data/                 — raw pulled data saved locally
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

SESSIONS_ROOT = Path(__file__).parent / "sessions"
SESSIONS_ROOT.mkdir(exist_ok=True)


class ResearchSession:
    """One isolated research session for one company."""

    def __init__(self, ticker: str, session_dir: Path) -> None:
        self.ticker       = ticker.upper()
        self.session_dir  = session_dir
        self.session_id   = session_dir.name
        self.raw_data_dir = session_dir / "raw_data"
        self.raw_data_dir.mkdir(exist_ok=True)

    # ── File paths ────────────────────────────────────────────────────────────

    @property
    def session_meta_file(self) -> Path:   return self.session_dir / "session_meta.json"
    @property
    def sources_file(self) -> Path:        return self.session_dir / "sources.json"
    @property
    def insights_file(self) -> Path:       return self.session_dir / "insights.json"
    @property
    def assumptions_file(self) -> Path:    return self.session_dir / "assumptions.json"
    @property
    def assumptions_history_file(self) -> Path: return self.session_dir / "assumptions_history.json"
    @property
    def guardrail_log_file(self) -> Path:  return self.session_dir / "guardrail_log.json"
    @property
    def hash_registry_file(self) -> Path:  return self.session_dir / "hash_registry.json"
    @property
    def llm_cache_file(self) -> Path:      return self.session_dir / "llm_cache.json"
    @property
    def scenarios_file(self) -> Path:      return self.session_dir / "scenarios.json"
    @property
    def audit_log_file(self) -> Path:      return self.session_dir / "audit_log.json"
    @property
    def summary_file(self) -> Path:        return self.session_dir / "summary.md"

    # ── Session meta (thesis / catalyst / variant view) ───────────────────────

    def get_meta(self) -> dict[str, Any]:
        if not self.session_meta_file.exists():
            return {}
        return json.loads(self.session_meta_file.read_text())

    def _save_meta(self, meta: dict[str, Any]) -> None:
        meta["_updated_at"] = _now()
        self.session_meta_file.write_text(json.dumps(meta, indent=2))

    def update_thesis(self, thesis: str) -> None:
        """Record the research hypothesis / thesis for this session."""
        meta = self.get_meta()
        meta["thesis"] = thesis
        self._save_meta(meta)
        self.audit("thesis_updated", f"Thesis: {thesis}")
        logger.info(f"[session/{self.ticker}] Thesis updated: {thesis[:80]}")

    def update_variant_view(self, variant_view: str) -> None:
        """Record what makes this model different from consensus."""
        meta = self.get_meta()
        meta["variant_view"] = variant_view
        self._save_meta(meta)
        self.audit("variant_view_updated", variant_view)

    def update_price_target(self, price_target: float, scenario: str = "base") -> None:
        """Record the price target for this session."""
        meta = self.get_meta()
        if "price_targets" not in meta:
            meta["price_targets"] = {}
        meta["price_targets"][scenario] = price_target
        self._save_meta(meta)

    def log_catalyst(
        self,
        description: str,
        expected_date: Optional[str] = None,  # "YYYY-MM-DD" or "Q1 FY26"
        catalyst_type: str = "earnings",       # earnings | regulatory | macro | corporate
    ) -> None:
        """
        Log a catalyst that determines timing of re-rating.
        From Section 13: 'Catalysts determine timing — earnings dates,
        FDA calendars, index rebalancing dates all tracked with alert triggers'
        """
        meta = self.get_meta()
        if "catalysts" not in meta:
            meta["catalysts"] = []
        meta["catalysts"].append({
            "description":   description,
            "expected_date": expected_date,
            "type":          catalyst_type,
            "logged_at":     _now(),
        })
        self._save_meta(meta)
        self.audit("catalyst_logged", f"{catalyst_type}: {description}")
        logger.info(f"[session/{self.ticker}] Catalyst: {description}")

    def get_thesis(self) -> Optional[str]:
        return self.get_meta().get("thesis")

    def get_catalysts(self) -> list[dict]:
        return self.get_meta().get("catalysts", [])

    def get_variant_view(self) -> Optional[str]:
        return self.get_meta().get("variant_view")

    # ── Source logging ────────────────────────────────────────────────────────

    def log_source(
        self,
        source_type: str,
        name: str,
        url_or_path: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        entry = {
            "source_type": source_type,
            "name":        name,
            "url_or_path": url_or_path,
            "description": description,
            "timestamp":   _now(),
        }
        _append_json_list(self.sources_file, entry)
        logger.debug(f"[session/{self.ticker}] Source: {name}")

    # ── Insight logging ───────────────────────────────────────────────────────

    def log_insight(
        self,
        signal_type: str,
        description: str,
        source_name: str,
        severity: str = "medium",
        factor: Optional[str] = None,
        raw_value: Optional[Any] = None,
    ) -> None:
        entry = {
            "signal_type": signal_type,
            "description": description,
            "source_name": source_name,
            "severity":    severity,
            "factor":      factor,
            "raw_value":   raw_value,
            "timestamp":   _now(),
        }
        _append_json_list(self.insights_file, entry)
        logger.info(f"[session/{self.ticker}] Insight [{severity}]: {description}")

    # ── Assumption management ─────────────────────────────────────────────────

    def get_assumptions(self) -> dict[str, Any]:
        if not self.assumptions_file.exists():
            return {}
        return json.loads(self.assumptions_file.read_text())

    def update_assumption(
        self,
        metric: str,
        new_value: float,
        reason: str,
        source: str,
        confidence: str = "medium",
        triggered_by: Optional[str] = None,
    ) -> dict[str, Any]:
        assumptions = self.get_assumptions()
        old_value   = assumptions.get(metric)
        assumptions[metric]      = new_value
        assumptions["_updated_at"] = _now()
        self.assumptions_file.write_text(json.dumps(assumptions, indent=2))
        _append_json_list(self.assumptions_history_file, {
            "metric":       metric,
            "old_value":    old_value,
            "new_value":    new_value,
            "reason":       reason,
            "source":       source,
            "confidence":   confidence,
            "triggered_by": triggered_by,
            "timestamp":    _now(),
        })
        logger.info(f"[session/{self.ticker}] {metric}: {old_value} → {new_value}")
        return assumptions

    def initialize_assumptions(self, base: dict[str, Any]) -> None:
        base["_initialized_at"] = _now()
        base["_session_id"]     = self.session_id
        base["_ticker"]         = self.ticker
        self.assumptions_file.write_text(json.dumps(base, indent=2))
        _append_json_list(self.assumptions_history_file, {
            "event":       "initialized",
            "assumptions": base,
            "timestamp":   _now(),
        })
        logger.info(f"[session/{self.ticker}] Initialized {len(base)} assumptions")

    # ── Guardrail logging ─────────────────────────────────────────────────────

    def log_guardrail_breach(self, metric: str, attempted_value: float,
                              capped_value: float, rule: str) -> None:
        _append_json_list(self.guardrail_log_file, {
            "metric":          metric,
            "attempted_value": attempted_value,
            "capped_value":    capped_value,
            "rule":            rule,
            "timestamp":       _now(),
        })
        logger.warning(f"[session/{self.ticker}] GUARDRAIL {metric}: {attempted_value:.2f} → {capped_value:.2f}")

    # ── Data hashing ──────────────────────────────────────────────────────────

    def register_data_hash(self, source_name: str, raw_data: bytes | str) -> str:
        if isinstance(raw_data, str):
            raw_data = raw_data.encode()
        sha = hashlib.sha256(raw_data).hexdigest()
        registry = {}
        if self.hash_registry_file.exists():
            registry = json.loads(self.hash_registry_file.read_text())
        prev = registry.get(source_name, {})
        if prev.get("hash") and prev["hash"] != sha:
            logger.warning(f"[session/{self.ticker}] DATA CHANGE: {source_name}")
        registry[source_name] = {"hash": sha, "timestamp": _now()}
        self.hash_registry_file.write_text(json.dumps(registry, indent=2))
        return sha

    def save_raw_data(self, source_name: str, content: str | bytes, suffix: str = ".json") -> Path:
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source_name}_{ts}{suffix}"
        path     = self.raw_data_dir / filename
        if isinstance(content, str):
            path.write_text(content)
        else:
            path.write_bytes(content)
        return path

    # ── LLM cache ────────────────────────────────────────────────────────────

    def get_llm_cache(self, cache_key: str) -> Optional[str]:
        if not self.llm_cache_file.exists():
            return None
        return json.loads(self.llm_cache_file.read_text()).get(cache_key)

    def set_llm_cache(self, cache_key: str, output: str) -> None:
        cache = {}
        if self.llm_cache_file.exists():
            cache = json.loads(self.llm_cache_file.read_text())
        cache[cache_key] = output
        self.llm_cache_file.write_text(json.dumps(cache, indent=2))

    # ── Scenarios ────────────────────────────────────────────────────────────

    def write_scenarios(self, scenarios: dict[str, Any]) -> None:
        scenarios["_generated_at"] = _now()
        self.scenarios_file.write_text(json.dumps(scenarios, indent=2))
        # Also update price targets in meta
        for label in ("bull", "base", "bear"):
            sc = scenarios.get("scenarios", {}).get(label, {})
            if sc.get("price_per_share"):
                self.update_price_target(sc["price_per_share"], scenario=label)
        logger.info(f"[session/{self.ticker}] Scenarios written.")

    def get_scenarios(self) -> dict[str, Any]:
        if not self.scenarios_file.exists():
            return {}
        return json.loads(self.scenarios_file.read_text())

    # ── Audit log ────────────────────────────────────────────────────────────

    def audit(self, event_type: str, detail: str, user_input: Optional[str] = None) -> None:
        _append_json_list(self.audit_log_file, {
            "event_type": event_type,
            "detail":     detail,
            "user_input": user_input,
            "timestamp":  _now(),
        })

    # ── Summary ───────────────────────────────────────────────────────────────

    def write_summary(self, markdown: str) -> None:
        self.summary_file.write_text(markdown)
        logger.info(f"[session/{self.ticker}] Summary written.")

    # ── Meta ─────────────────────────────────────────────────────────────────

    def meta(self) -> dict[str, Any]:
        m = self.get_meta()
        return {
            "session_id":         self.session_id,
            "ticker":             self.ticker,
            "thesis":             m.get("thesis"),
            "variant_view":       m.get("variant_view"),
            "catalysts":          m.get("catalysts", []),
            "price_targets":      m.get("price_targets", {}),
            "has_assumptions":    self.assumptions_file.exists(),
            "has_scenarios":      self.scenarios_file.exists(),
            "source_count":       len(_read_json_list(self.sources_file)),
            "insight_count":      len(_read_json_list(self.insights_file)),
            "assumption_changes": len(_read_json_list(self.assumptions_history_file)),
            "guardrail_breaches": len(_read_json_list(self.guardrail_log_file)),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Session factory
# ─────────────────────────────────────────────────────────────────────────────

def new_session(
    ticker: str,
    hypothesis: Optional[str] = None,    # research question / thesis
    variant_view: Optional[str] = None,  # what makes this different from consensus
    catalysts: Optional[list[dict]] = None,  # upcoming events that will re-rate the stock
) -> ResearchSession:
    """
    Create a new isolated session folder.

    Args:
        ticker:       NSE/BSE ticker symbol
        hypothesis:   Research question anchoring the session.
                      From Section 13: "Anchor to a hypothesis, not data"
        variant_view: What makes your model different from consensus.
                      From Section 13: "Document and track variant view"
        catalysts:    List of upcoming events expected to re-rate the stock.
                      From Section 13: "Catalysts determine timing"
    """
    ticker     = ticker.upper().strip()
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"{ticker}_{ts}"
    session_dir = SESSIONS_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "session_id":   session_id,
        "ticker":       ticker,
        "created_at":   _now(),
        "status":       "active",
        "thesis":       hypothesis or "",
        "variant_view": variant_view or "",
        "catalysts":    catalysts or [],
        "price_targets": {},
    }
    (session_dir / "session_meta.json").write_text(json.dumps(meta, indent=2))

    logger.info(f"[session_manager] New session: {session_id}")
    if hypothesis:
        logger.info(f"[session_manager] Hypothesis: {hypothesis}")
    return ResearchSession(ticker=ticker, session_dir=session_dir)


def load_session(session_id: str) -> ResearchSession:
    session_dir = SESSIONS_ROOT / session_id
    if not session_dir.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")
    meta_file = session_dir / "session_meta.json"
    meta      = json.loads(meta_file.read_text()) if meta_file.exists() else {}
    ticker    = meta.get("ticker", session_id.split("_")[0])
    return ResearchSession(ticker=ticker, session_dir=session_dir)


def list_sessions(ticker: Optional[str] = None) -> list[dict[str, Any]]:
    sessions = []
    for d in sorted(SESSIONS_ROOT.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        meta_file = d / "session_meta.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {"session_id": d.name, "ticker": d.name.split("_")[0]}
        if ticker and meta.get("ticker", "").upper() != ticker.upper():
            continue
        sessions.append(meta)
    return sessions


def latest_session(ticker: str) -> Optional[ResearchSession]:
    sessions = list_sessions(ticker=ticker)
    if not sessions:
        return None
    return load_session(sessions[0]["session_id"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _append_json_list(path: Path, entry: dict) -> None:
    data = _read_json_list(path)
    data.append(entry)
    path.write_text(json.dumps(data, indent=2))

def _read_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text())
    except Exception:
        return []
