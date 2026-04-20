"""
ai_engine/version_control.py
──────────────────────────────
Layer 10 — Version Control + Snapshot Hashing.

Responsibilities:
  - Full assumption history with rollback to any point
  - Hash every raw data pull — flags if source data changes between sessions
  - Detect data drift: same source, different hash = upstream data was revised
  - Cross-session comparison: how did assumptions evolve over time?
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.session_manager import ResearchSession, SESSIONS_ROOT


# ── Snapshot hashing ──────────────────────────────────────────────────────────

def hash_data(data: str | bytes | dict | list) -> str:
    """Return SHA-256 hex of any serialisable data."""
    if isinstance(data, (dict, list)):
        raw = json.dumps(data, sort_keys=True, default=str).encode()
    elif isinstance(data, str):
        raw = data.encode()
    else:
        raw = data
    return hashlib.sha256(raw).hexdigest()


def register_snapshot(
    session: ResearchSession,
    source_name: str,
    data: str | bytes | dict | list,
    metadata: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Hash a data pull and store in hash_registry.json.

    If this source was seen before in a PREVIOUS session for the same ticker,
    compare hashes to detect upstream data changes.

    Returns registry entry dict.
    """
    sha = hash_data(data)
    ts  = datetime.now(timezone.utc).isoformat()

    # Load current registry
    registry: dict[str, Any] = {}
    if session.hash_registry_file.exists():
        registry = json.loads(session.hash_registry_file.read_text())

    prev = registry.get(source_name)
    changed = False
    if prev and prev.get("hash") != sha:
        changed = True
        logger.warning(
            f"[version_control] DATA CHANGE DETECTED: {source_name} "
            f"previous={prev['hash'][:12]}... current={sha[:12]}..."
        )
        session.audit(
            "data_change_detected",
            f"{source_name}: hash changed since {prev.get('timestamp','?')}",
        )

    entry = {
        "hash":      sha,
        "timestamp": ts,
        "changed":   changed,
        "metadata":  metadata or {},
    }
    registry[source_name] = entry
    session.hash_registry_file.write_text(json.dumps(registry, indent=2))
    return entry


def check_cross_session_drift(ticker: str, source_name: str) -> list[dict[str, Any]]:
    """
    Compare hash_registry entries for the same source across all past sessions
    for this ticker. Returns list of entries showing how data changed over time.
    """
    from ai_engine.session_manager import list_sessions, load_session

    sessions = list_sessions(ticker=ticker)
    history: list[dict[str, Any]] = []

    for meta in sessions:
        try:
            s = load_session(meta["session_id"])
            if not s.hash_registry_file.exists():
                continue
            registry = json.loads(s.hash_registry_file.read_text())
            if source_name in registry:
                history.append({
                    "session_id": meta["session_id"],
                    "timestamp":  registry[source_name].get("timestamp"),
                    "hash":       registry[source_name].get("hash", "")[:16] + "...",
                    "changed":    registry[source_name].get("changed", False),
                })
        except Exception:
            continue

    return history


# ── Assumption version control ────────────────────────────────────────────────

def get_assumption_history(session: ResearchSession) -> list[dict[str, Any]]:
    """Return full assumption change history for this session."""
    if not session.assumptions_history_file.exists():
        return []
    return json.loads(session.assumptions_history_file.read_text())


def get_assumption_at_index(
    session: ResearchSession,
    index: int,
) -> dict[str, Any]:
    """Return the assumptions state after `index` changes were applied."""
    history = get_assumption_history(session)
    if not history:
        return {}

    # Find initialization record (always first)
    state: dict[str, Any] = {}
    changes_applied = 0

    for i, entry in enumerate(history):
        if entry.get("event") == "initialized" and "assumptions" in entry:
            state = dict(entry["assumptions"])
            continue
        if "metric" in entry:
            if changes_applied >= index:
                break
            metric = entry["metric"]
            new_val = entry.get("new_value")
            if new_val is not None:
                state[metric] = new_val
            changes_applied += 1

    return state


def rollback_to_index(session: ResearchSession, index: int) -> dict[str, Any]:
    """
    Restore assumptions to the state after `index` changes were applied.
    Index 0 = initial assumptions, 1 = after first change, etc.
    """
    target = get_assumption_at_index(session, index)
    if not target:
        raise ValueError(f"Cannot roll back to index {index} — no history.")

    target["_rolled_back_to_index"] = index
    target["_rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    session.assumptions_file.write_text(json.dumps(target, indent=2))

    session.audit(
        "rollback",
        f"Assumptions rolled back to index {index}",
    )
    logger.info(f"[version_control] Rolled back {session.ticker} to assumption index {index}")
    return target


def diff_assumptions(
    old: dict[str, Any],
    new: dict[str, Any],
    skip_keys: Optional[set[str]] = None,
) -> list[dict[str, Any]]:
    """Return a list of changed assumption metrics between two snapshots."""
    skip = skip_keys or {"_updated_at", "_initialized_at", "_session_id", "_ticker",
                         "_rolled_back_to_index", "_rolled_back_at"}
    changes: list[dict[str, Any]] = []

    all_keys = set(old.keys()) | set(new.keys())
    for key in sorted(all_keys):
        if key in skip:
            continue
        ov = old.get(key)
        nv = new.get(key)
        if ov != nv:
            try:
                delta = float(nv) - float(ov) if ov is not None and nv is not None else None
            except (TypeError, ValueError):
                delta = None
            changes.append({
                "metric":    key,
                "old_value": ov,
                "new_value": nv,
                "delta":     round(delta, 4) if delta is not None else None,
            })
    return changes


# ── Cross-session assumption comparison ───────────────────────────────────────

def compare_sessions(ticker: str, session_a_id: str, session_b_id: str) -> list[dict[str, Any]]:
    """Compare final assumptions between two sessions for the same ticker."""
    from ai_engine.session_manager import load_session

    sa = load_session(session_a_id)
    sb = load_session(session_b_id)
    return diff_assumptions(sa.get_assumptions(), sb.get_assumptions())
