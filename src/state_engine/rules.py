"""
Deterministic rules for the RecoverAI Financial State Engine.

Rule IDs:
- STATE-RULE-000: Data/settlement validation and impossible transition detection (EXCEPTION / ESCALATE)
- STATE-RULE-001: FAILED followed by AUTHORIZED/CAPTURED (late auth flip) (ALREADY_RECOVERED / STOP)
- STATE-RULE-002: Another successful payment attempt for the same order (ALREADY_RECOVERED / STOP)
- STATE-RULE-003: Clean successful authorization/capture (ALREADY_RECOVERED / STOP)
- STATE-RULE-004: Pending/unresolved/in-flight payment (UNCERTAIN / WAIT)
- STATE-RULE-005: Definitive unrecovered failure (VERIFIED_LOST / EVALUATE_RECOVERY)
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from .models import FinancialState, RecommendedAction, Event, PaymentRecord, StateEvaluationResult


SUCCESS_EVENTS = {"payment.authorized", "payment.captured"}
TERMINAL_SUCCESS = "payment.captured"
FAILURE_EVENTS = {"payment.failed"}
PENDING_EVENTS = {"payment.pending"}
CREATION_EVENTS = {"payment.created"}
REFUND_EVENTS = {"payment.refunded"}


def parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO timestamp safely, returning UTC offset-aware datetime or None if invalid."""
    if not ts_str:
        return None
    try:
        clean_ts = str(ts_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None



def deduplicate_events(events: List[Event]) -> List[Event]:
    """
    Deduplicate identical events idempotently while preserving order.
    """
    seen = set()
    deduped = []
    for ev in events:
        key = (
            ev.event,
            ev.payment_id,
            ev.order_id,
            ev.amount,
            ev.ts,
            ev.error_code,
            ev.error_description,
            ev.hardness,
            ev.late_authorization,
        )
        if key not in seen:
            seen.add(key)
            deduped.append(ev)
    return deduped


def sort_events_chronologically(events: List[Event]) -> Tuple[List[Event], bool]:
    """
    Sort events chronologically by timestamp.
    Returns (sorted_events, all_timestamps_valid).
    """
    parsed_with_ev = []
    for ev in events:
        if ev.ts is None:
            # Event without timestamp cannot be safely ordered
            return events, False
        parsed_dt = parse_timestamp(ev.ts)
        if parsed_dt is None:
            return events, False
        parsed_with_ev.append((parsed_dt, ev))

    parsed_with_ev.sort(key=lambda x: x[0])
    return [ev for _, ev in parsed_with_ev], True


def evaluate_state_rules(
    payment: PaymentRecord,
    payment_events: List[Event],
    order_events: Optional[List[Event]] = None,
    evaluation_ts: Optional[str] = None,
) -> StateEvaluationResult:
    """
    Main rule evaluation pipeline executing STATE-RULE-000 through STATE-RULE-005 deterministically.
    """
    now_iso = evaluation_ts or datetime.now(timezone.utc).isoformat()
    pid = payment.payment_id
    oid = payment.order_id

    # -------------------------------------------------------------
    # STATE-RULE-000: Data Validation, Settlement Consistency & Impossible Transitions
    # -------------------------------------------------------------
    if not pid or not isinstance(pid, str) or not pid.strip():
        return StateEvaluationResult(
            payment_id=pid or "UNKNOWN",
            order_id=oid,
            state=FinancialState.EXCEPTION,
            recommended_action=RecommendedAction.ESCALATE,
            reason="Validation failed: Missing or invalid payment ID.",
            evidence_events=[],
            evaluated_at=now_iso,
            rule_id="STATE-RULE-000",
        )

    # Validate timestamps and sort payment events chronologically
    sorted_events, valid_ts = sort_events_chronologically(payment_events)
    if not valid_ts and len(payment_events) > 0:
        return StateEvaluationResult(
            payment_id=pid,
            order_id=oid,
            state=FinancialState.EXCEPTION,
            recommended_action=RecommendedAction.ESCALATE,
            reason="Validation failed: One or more events have missing or invalid timestamp formats.",
            evidence_events=[ev.event for ev in payment_events],
            evaluated_at=now_iso,
            rule_id="STATE-RULE-000",
        )

    deduped_events = deduplicate_events(sorted_events)
    event_names = [e.event for e in deduped_events]

    # Settlement validation if settlement data is present
    if payment.has_settlement is True:
        if payment.settlement_matches_order is False:
            return StateEvaluationResult(
                payment_id=pid,
                order_id=oid,
                state=FinancialState.EXCEPTION,
                recommended_action=RecommendedAction.ESCALATE,
                reason=f"Settlement mismatch: Payment {pid} has settlement recorded but settlement_matches_order is False.",
                evidence_events=event_names,
                evaluated_at=now_iso,
                rule_id="STATE-RULE-000",
            )
        if (
            payment.settled_amount is not None
            and payment.amount is not None
            and abs(float(payment.settled_amount) - float(payment.amount)) > 0.01
        ):
            return StateEvaluationResult(
                payment_id=pid,
                order_id=oid,
                state=FinancialState.EXCEPTION,
                recommended_action=RecommendedAction.ESCALATE,
                reason=(
                    f"Settlement amount mismatch: Settled amount ({payment.settled_amount}) "
                    f"does not match payment amount ({payment.amount})."
                ),
                evidence_events=event_names,
                evaluated_at=now_iso,
                rule_id="STATE-RULE-000",
            )

    # Impossible state transitions check
    # 1. Refund without preceding capture
    has_capture_before_refund = False
    for ev in deduped_events:
        if ev.event == "payment.captured":
            has_capture_before_refund = True
        elif ev.event == "payment.refunded" and not has_capture_before_refund:
            return StateEvaluationResult(
                payment_id=pid,
                order_id=oid,
                state=FinancialState.EXCEPTION,
                recommended_action=RecommendedAction.ESCALATE,
                reason="Impossible state transition: Refund event received without prior successful capture.",
                evidence_events=event_names,
                evaluated_at=now_iso,
                rule_id="STATE-RULE-000",
            )

    # 2. Captured followed by failure
    has_captured = False
    for ev in deduped_events:
        if ev.event == "payment.captured":
            has_captured = True
        elif ev.event == "payment.failed" and has_captured:
            return StateEvaluationResult(
                payment_id=pid,
                order_id=oid,
                state=FinancialState.EXCEPTION,
                recommended_action=RecommendedAction.ESCALATE,
                reason="Impossible state transition: Payment failure occurred after payment was already captured.",
                evidence_events=event_names,
                evaluated_at=now_iso,
                rule_id="STATE-RULE-000",
            )

    # -------------------------------------------------------------
    # STATE-RULE-001: Late Authorization Flip (FAILED -> AUTHORIZED/CAPTURED)
    # -------------------------------------------------------------
    failed_indices = [i for i, e in enumerate(deduped_events) if e.event == "payment.failed"]
    success_indices = [i for i, e in enumerate(deduped_events) if e.event in SUCCESS_EVENTS]
    has_late_auth_flag = any(e.late_authorization is True for e in deduped_events)

    if failed_indices and (success_indices or has_late_auth_flag):
        # Check if any success event occurred AFTER the failure event
        first_fail_idx = min(failed_indices)
        last_success_idx = max(success_indices) if success_indices else -1
        if last_success_idx > first_fail_idx or has_late_auth_flag:
            return StateEvaluationResult(
                payment_id=pid,
                order_id=oid,
                state=FinancialState.ALREADY_RECOVERED,
                recommended_action=RecommendedAction.STOP,
                reason="Payment initially failed but was subsequently authorized/captured (late authorization flip-flop).",
                evidence_events=event_names,
                evaluated_at=now_iso,
                rule_id="STATE-RULE-001",
            )

    # -------------------------------------------------------------
    # STATE-RULE-002: Order-Level Multi-Attempt Recovery
    # -------------------------------------------------------------
    if order_events and oid:
        # Group order events by payment attempt
        other_payments: Dict[str, List[Event]] = {}
        for ev in order_events:
            ev_pid = ev.payment_id
            if ev_pid and ev_pid != pid:
                other_payments.setdefault(ev_pid, []).append(ev)

        for other_pid, other_evs in other_payments.items():
            sorted_other, _ = sort_events_chronologically(other_evs)
            has_other_success = any(e.event in SUCCESS_EVENTS for e in sorted_other)
            # Make sure it didn't fail after success without recovery
            if has_other_success:
                return StateEvaluationResult(
                    payment_id=pid,
                    order_id=oid,
                    state=FinancialState.ALREADY_RECOVERED,
                    recommended_action=RecommendedAction.STOP,
                    reason=(
                        f"Payment attempt failed, but order {oid} was successfully recovered "
                        f"via another successful payment attempt ({other_pid})."
                    ),
                    evidence_events=event_names + [f"{other_pid}:{e.event}" for e in sorted_other],
                    evaluated_at=now_iso,
                    rule_id="STATE-RULE-002",
                )

    # -------------------------------------------------------------
    # STATE-RULE-003: Clean Successful Authorization / Capture
    # -------------------------------------------------------------
    if not failed_indices and (success_indices or (payment.has_settlement is True and payment.settlement_matches_order is True)):
        return StateEvaluationResult(
            payment_id=pid,
            order_id=oid,
            state=FinancialState.ALREADY_RECOVERED,
            recommended_action=RecommendedAction.STOP,
            reason="Payment was successfully authorized and captured without terminal failure.",
            evidence_events=event_names if event_names else ["settlement.verified"],
            evaluated_at=now_iso,
            rule_id="STATE-RULE-003",
        )

    # -------------------------------------------------------------
    # STATE-RULE-004: Pending / Unresolved / In-Flight State
    # -------------------------------------------------------------
    # If the scenario explicitly indicates uncertain_pending or the latest event is pending / unresolved creation
    is_scenario_uncertain = payment.scenario == "uncertain_pending"
    has_pending_event = any(e.event in PENDING_EVENTS for e in deduped_events)
    last_event_is_pending = bool(deduped_events and deduped_events[-1].event in PENDING_EVENTS)
    only_created = bool(deduped_events and all(e.event in CREATION_EVENTS for e in deduped_events))
    
    # FAILED followed by PENDING
    failed_then_pending = False
    if failed_indices and has_pending_event:
        first_fail_idx = min(failed_indices)
        pending_indices = [i for i, e in enumerate(deduped_events) if e.event in PENDING_EVENTS]
        if any(p_idx > first_fail_idx for p_idx in pending_indices):
            failed_then_pending = True

    if is_scenario_uncertain or last_event_is_pending or only_created or failed_then_pending:
        return StateEvaluationResult(
            payment_id=pid,
            order_id=oid,
            state=FinancialState.UNCERTAIN,
            recommended_action=RecommendedAction.WAIT,
            reason="Payment status is pending, in-flight, or within an active retry window; awaiting final resolution.",
            evidence_events=event_names,
            evaluated_at=now_iso,
            rule_id="STATE-RULE-004",
        )

    # -------------------------------------------------------------
    # STATE-RULE-005: Definitive Unrecovered Failure (VERIFIED_LOST)
    # -------------------------------------------------------------
    if failed_indices:
        last_fail_event = [e for e in deduped_events if e.event == "payment.failed"][-1]
        err_code = last_fail_event.error_code or "UNKNOWN"
        err_desc = last_fail_event.error_description or "Payment failed"
        hardness = f" [{last_fail_event.hardness}]" if last_fail_event.hardness else ""
        return StateEvaluationResult(
            payment_id=pid,
            order_id=oid,
            state=FinancialState.VERIFIED_LOST,
            recommended_action=RecommendedAction.EVALUATE_RECOVERY,
            reason=f"Payment failure confirmed{hardness} ({err_code}: {err_desc}) with no subsequent successful recovery.",
            evidence_events=event_names,
            evaluated_at=now_iso,
            rule_id="STATE-RULE-005",
        )

    # Fallback for empty or unrecognized event sequences
    if not deduped_events:
        return StateEvaluationResult(
            payment_id=pid,
            order_id=oid,
            state=FinancialState.UNCERTAIN,
            recommended_action=RecommendedAction.WAIT,
            reason="No event history found for payment; awaiting lifecycle events.",
            evidence_events=[],
            evaluated_at=now_iso,
            rule_id="STATE-RULE-004",
        )

    return StateEvaluationResult(
        payment_id=pid,
        order_id=oid,
        state=FinancialState.EXCEPTION,
        recommended_action=RecommendedAction.ESCALATE,
        reason="Unable to determine financial state: unhandled event combination.",
        evidence_events=event_names,
        evaluated_at=now_iso,
        rule_id="STATE-RULE-000",
    )
