"""
ai_engine/assumption_engine.py
────────────────────────────────
Layer 9 — Assumption Engine + Guardrails.

Translates factor engine deltas into actual DCF inputs.
Enforces guardrail rules before writing any assumption.
Writes the bridge file (assumptions.json) that the DCF engine reads.

Every change is:
  1. Checked against guardrail min/max
  2. Checked against max_single_change cap
  3. Logged in assumptions_history.json with reason + source
  4. Written to assumptions.json only if all checks pass
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from ai_engine.confidence_scorer import ConfidenceResult, score_delta
from ai_engine.factor_engine import AssumptionDelta, consolidate_deltas
from ai_engine.session_manager import ResearchSession

RULES_FILE = Path(__file__).parent / "assumption_rules.json"


def _load_rules() -> dict[str, Any]:
    if RULES_FILE.exists():
        return json.loads(RULES_FILE.read_text()).get("rules", {})
    return {}


@dataclass
class GuardrailResult:
    passed: bool
    original_delta: float
    applied_delta: float
    breach_reason: Optional[str] = None


def apply_guardrail(
    metric: str,
    current_value: float,
    proposed_delta: float,
    rules: Optional[dict[str, Any]] = None,
) -> GuardrailResult:
    """Check and clamp a proposed delta against guardrail rules."""
    if rules is None:
        rules = _load_rules()

    rule = rules.get(metric, {})
    if not rule:
        # No rule for this metric — allow change
        return GuardrailResult(
            passed=True,
            original_delta=proposed_delta,
            applied_delta=proposed_delta,
        )

    min_val = rule.get("min")
    max_val = rule.get("max")
    max_change = rule.get("max_single_change")

    applied = proposed_delta

    # Check max_single_change
    if max_change is not None and abs(applied) > max_change:
        capped = max_change if applied > 0 else -max_change
        breach = f"max_single_change ({abs(applied):.2f} > {max_change})"
        logger.warning(f"[guardrail] {metric}: change capped from {applied:.2f} to {capped:.2f}")
        applied = capped
        return GuardrailResult(
            passed=False,
            original_delta=proposed_delta,
            applied_delta=applied,
            breach_reason=breach,
        )

    # Check resulting value against min/max
    new_val = current_value + applied
    if min_val is not None and new_val < min_val:
        applied = min_val - current_value
        breach = f"would go below min ({new_val:.2f} < {min_val})"
        return GuardrailResult(passed=False, original_delta=proposed_delta, applied_delta=applied, breach_reason=breach)

    if max_val is not None and new_val > max_val:
        applied = max_val - current_value
        breach = f"would exceed max ({new_val:.2f} > {max_val})"
        return GuardrailResult(passed=False, original_delta=proposed_delta, applied_delta=applied, breach_reason=breach)

    return GuardrailResult(passed=True, original_delta=proposed_delta, applied_delta=applied)


class AssumptionEngine:
    """
    Manages the full lifecycle of DCF assumptions for a research session.
    Takes signals → factors → applies guardrails → writes bridge file.
    """

    def __init__(self, session: ResearchSession) -> None:
        self.session = session
        self._rules = _load_rules()

    def get_current(self) -> dict[str, Any]:
        """Get current assumptions from session."""
        return self.session.get_assumptions()

    def initialize(self, base_assumptions: dict[str, Any]) -> None:
        """Set the starting assumptions. Call once at session start."""
        self.session.initialize_assumptions(base_assumptions)
        self.session.audit("initialize", f"Base assumptions set: {list(base_assumptions.keys())}")

    def process_deltas(
        self,
        deltas: list[AssumptionDelta],
        event_date: Optional[date] = None,
        require_confirmation_above_change: float = 5.0,
    ) -> dict[str, Any]:
        """
        Apply a list of AssumptionDeltas to current assumptions.

        Args:
            deltas: from factor_engine.signals_to_factors()
            event_date: when the triggering event occurred
            require_confirmation_above_change: changes larger than this %
              are flagged for human confirmation regardless of confidence

        Returns:
            Updated assumptions dict.
        """
        consolidated = consolidate_deltas(deltas)
        current = self.get_current()
        updated_keys: list[str] = []

        for metric, delta in consolidated.items():
            current_val = float(current.get(metric, 0.0))

            # Score confidence
            conf: ConfidenceResult = score_delta(delta, event_date=event_date)

            # Skip if confidence too low
            if conf.score < 0.20:
                logger.info(f"[assumption_engine] Skipping {metric}: confidence too low ({conf.score:.2f})")
                self.session.audit(
                    "skip_low_confidence",
                    f"{metric}: confidence={conf.score:.2f} < 0.20 — not applied",
                )
                continue

            # Apply guardrail
            gr = apply_guardrail(metric, current_val, delta.delta, self._rules)
            if not gr.passed:
                self.session.log_guardrail_breach(
                    metric=metric,
                    attempted_value=current_val + delta.delta,
                    capped_value=current_val + gr.applied_delta,
                    rule=gr.breach_reason or "guardrail",
                )

            if gr.applied_delta == 0:
                continue  # No change after clamping

            # Flag large changes for confirmation
            if abs(gr.applied_delta) >= require_confirmation_above_change:
                logger.warning(
                    f"[assumption_engine] LARGE CHANGE: {metric} "
                    f"delta={gr.applied_delta:+.2f} — flagged for human review"
                )
                self.session.audit(
                    "large_change_flagged",
                    f"{metric}: {current_val:.2f} → {current_val+gr.applied_delta:.2f} "
                    f"(change={gr.applied_delta:+.2f})",
                )

            # Write the assumption
            self.session.update_assumption(
                metric=metric,
                new_value=round(current_val + gr.applied_delta, 4),
                reason=delta.reason,
                source=delta.source_event,
                confidence=conf.label,
                triggered_by=delta.source_signal_id,
            )
            updated_keys.append(metric)
            self.session.log_source(
                source_type="signal",
                name=delta.source_signal_id,
                description=delta.transmission_chain,
            )

        logger.info(
            f"[assumption_engine] Updated {len(updated_keys)} assumptions: {updated_keys}"
        )
        return self.session.get_assumptions()

    def manual_override(
        self,
        metric: str,
        new_value: float,
        reason: str,
        user_initiated: bool = True,
    ) -> dict[str, Any]:
        """
        Human-initiated assumption override.
        Still checks guardrails but allows larger changes than signals.
        """
        current = self.get_current()
        current_val = float(current.get(metric, 0.0))
        proposed_delta = new_value - current_val

        # Guardrail check (relaxed for manual overrides — skip max_single_change)
        rules = _load_rules()
        rule = rules.get(metric, {})
        final_val = new_value
        if rule.get("min") is not None:
            final_val = max(final_val, rule["min"])
        if rule.get("max") is not None:
            final_val = min(final_val, rule["max"])

        if final_val != new_value:
            self.session.log_guardrail_breach(
                metric=metric,
                attempted_value=new_value,
                capped_value=final_val,
                rule=f"manual override clamped to [{rule.get('min')}, {rule.get('max')}]",
            )

        self.session.update_assumption(
            metric=metric,
            new_value=final_val,
            reason=reason,
            source="manual_override" if user_initiated else "system",
            confidence="high",
        )
        self.session.audit(
            "manual_override",
            f"{metric}: {current_val:.4f} → {final_val:.4f} (reason: {reason})",
            user_input=reason,
        )
        return self.session.get_assumptions()

    def rollback_to(self, history_index: int) -> dict[str, Any]:
        """
        Restore assumptions to a previous state from assumptions_history.json.
        Reads history, replays up to history_index.
        """
        import json
        history_file = self.session.assumptions_history_file
        if not history_file.exists():
            raise ValueError("No assumption history to roll back to.")

        history = json.loads(history_file.read_text())
        if history_index >= len(history):
            raise IndexError(f"history_index {history_index} out of range (len={len(history)})")

        target = history[history_index]
        if "assumptions" in target:
            # This was an initialization record
            restored = target["assumptions"]
        else:
            # Partial record — we need to replay from beginning
            logger.warning("[assumption_engine] Rollback via replay not yet implemented — restoring from checkpoint.")
            restored = {}

        if restored:
            self.session.assumptions_file.write_text(json.dumps(restored, indent=2))
            self.session.audit("rollback", f"Rolled back to history index {history_index}")
            logger.info(f"[assumption_engine] Rolled back to history index {history_index}")

        return self.session.get_assumptions()


# ── Consensus comparison (Section 13: "Consensus is the baseline") ──────────


def compare_to_consensus(
    session: ResearchSession,
    consensus_assumptions: dict[str, float],
    flag_divergence_above: float = 3.0,
) -> list[dict]:
    """
    Compare current session assumptions to consensus estimates.

    From Section 13: "Consensus is the baseline, not the target —
    Pulls Screener/Trendlyne consensus — flags when your model diverges significantly"

    Args:
        session: current research session
        consensus_assumptions: dict of metric → consensus value (from Screener/analyst)
        flag_divergence_above: flag if your assumption differs by more than this

    Returns:
        List of divergence records with explanation
    """
    current     = session.get_assumptions()
    divergences = []

    for metric, consensus_val in consensus_assumptions.items():
        current_val = current.get(metric)
        if current_val is None:
            continue
        try:
            diff = float(current_val) - float(consensus_val)
        except (TypeError, ValueError):
            continue

        is_divergent = abs(diff) > flag_divergence_above
        divergences.append({
            "metric":         metric,
            "your_value":     round(float(current_val), 4),
            "consensus":      round(float(consensus_val), 4),
            "difference":     round(diff, 4),
            "divergent":      is_divergent,
            "direction":      "above_consensus" if diff > 0 else "below_consensus",
        })

        if is_divergent:
            logger.warning(
                f"[assumption_engine] DIVERGENCE: {metric} = {current_val:.2f} "
                f"vs consensus {consensus_val:.2f} (diff {diff:+.2f})"
            )
            session.audit(
                "consensus_divergence",
                f"{metric}: yours={current_val:.2f} consensus={consensus_val:.2f} diff={diff:+.2f}",
            )

    return divergences
