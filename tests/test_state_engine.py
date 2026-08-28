"""
Unit and integration tests for RecoverAI Financial State Engine.
"""

import sys
from pathlib import Path
import pytest

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine import (
    FinancialStateEngine,
    FinancialState,
    RecommendedAction,
    Event,
    PaymentRecord,
)


@pytest.fixture
def engine():
    return FinancialStateEngine(evaluation_timestamp="2026-08-27T18:00:00Z")


# 1. FAILED only
def test_failed_only(engine):
    payment = PaymentRecord(payment_id="pay_001", order_id="order_001", amount=1000)
    events = [
        Event(event="payment.created", payment_id="pay_001", order_id="order_001", ts="2026-08-10T10:00:00Z"),
        Event(
            event="payment.failed",
            payment_id="pay_001",
            order_id="order_001",
            error_code="TIMEOUT",
            error_description="Collect request expired",
            hardness="soft",
            ts="2026-08-10T10:00:05Z",
        ),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.VERIFIED_LOST
    assert result.recommended_action == RecommendedAction.EVALUATE_RECOVERY
    assert result.rule_id == "STATE-RULE-005"
    assert "TIMEOUT" in result.reason


# 2. FAILED -> AUTHORIZED
def test_failed_to_authorized(engine):
    payment = PaymentRecord(payment_id="pay_002", order_id="order_002", amount=1500)
    events = [
        Event(event="payment.created", payment_id="pay_002", order_id="order_002", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_002", order_id="order_002", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.authorized", payment_id="pay_002", order_id="order_002", ts="2026-08-10T10:05:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.ALREADY_RECOVERED
    assert result.recommended_action == RecommendedAction.STOP
    assert result.rule_id == "STATE-RULE-001"


# 3. FAILED -> CAPTURED
def test_failed_to_captured(engine):
    payment = PaymentRecord(payment_id="pay_003", order_id="order_003", amount=2000)
    events = [
        Event(event="payment.created", payment_id="pay_003", order_id="order_003", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_003", order_id="order_003", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_003", order_id="order_003", ts="2026-08-10T10:06:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.ALREADY_RECOVERED
    assert result.recommended_action == RecommendedAction.STOP
    assert result.rule_id == "STATE-RULE-001"


# 4. FAILED -> PENDING
def test_failed_to_pending(engine):
    payment = PaymentRecord(payment_id="pay_004", order_id="order_004", amount=500)
    events = [
        Event(event="payment.created", payment_id="pay_004", order_id="order_004", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_004", order_id="order_004", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.pending", payment_id="pay_004", order_id="order_004", ts="2026-08-10T10:02:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.UNCERTAIN
    assert result.recommended_action == RecommendedAction.WAIT
    assert result.rule_id == "STATE-RULE-004"


# 5. FAILED -> REFUNDED (Impossible transition)
def test_failed_to_refunded_impossible(engine):
    payment = PaymentRecord(payment_id="pay_005", order_id="order_005", amount=750)
    events = [
        Event(event="payment.created", payment_id="pay_005", order_id="order_005", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_005", order_id="order_005", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.refunded", payment_id="pay_005", order_id="order_005", ts="2026-08-10T10:01:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.EXCEPTION
    assert result.recommended_action == RecommendedAction.ESCALATE
    assert result.rule_id == "STATE-RULE-000"
    assert "Impossible state transition" in result.reason


# 6. Duplicate order recovery (FAILED payment + successful payment for same order)
def test_failed_payment_with_order_level_recovery(engine):
    payment_a = PaymentRecord(payment_id="pay_006_A", order_id="order_006", amount=999)
    events_a = [
        Event(event="payment.created", payment_id="pay_006_A", order_id="order_006", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_006_A", order_id="order_006", ts="2026-08-10T10:00:05Z"),
    ]
    order_events = events_a + [
        Event(event="payment.created", payment_id="pay_006_B", order_id="order_006", ts="2026-08-10T10:01:00Z"),
        Event(event="payment.authorized", payment_id="pay_006_B", order_id="order_006", ts="2026-08-10T10:01:08Z"),
        Event(event="payment.captured", payment_id="pay_006_B", order_id="order_006", ts="2026-08-10T10:01:12Z"),
    ]
    result = engine.evaluate_payment(payment_a, events=events_a, order_events=order_events)
    assert result.state == FinancialState.ALREADY_RECOVERED
    assert result.recommended_action == RecommendedAction.STOP
    assert result.rule_id == "STATE-RULE-002"
    assert "pay_006_B" in result.reason


# 7. Multiple failed attempts for same order
def test_multiple_failed_attempts(engine):
    payment_a = PaymentRecord(payment_id="pay_007_A", order_id="order_007", amount=2499)
    events_a = [
        Event(event="payment.created", payment_id="pay_007_A", order_id="order_007", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_007_A", order_id="order_007", ts="2026-08-10T10:00:05Z"),
    ]
    order_events = events_a + [
        Event(event="payment.created", payment_id="pay_007_B", order_id="order_007", ts="2026-08-10T10:02:00Z"),
        Event(event="payment.failed", payment_id="pay_007_B", order_id="order_007", ts="2026-08-10T10:02:05Z"),
    ]
    result = engine.evaluate_payment(payment_a, events=events_a, order_events=order_events)
    assert result.state == FinancialState.VERIFIED_LOST
    assert result.recommended_action == RecommendedAction.EVALUATE_RECOVERY
    assert result.rule_id == "STATE-RULE-005"


# 8. Duplicate event handling
def test_duplicate_events_idempotency(engine):
    payment = PaymentRecord(payment_id="pay_008", order_id="order_008", amount=1200)
    events = [
        Event(event="payment.created", payment_id="pay_008", order_id="order_008", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.created", payment_id="pay_008", order_id="order_008", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_008", order_id="order_008", ts="2026-08-10T10:00:05Z"),
        Event(event="payment.captured", payment_id="pay_008", order_id="order_008", ts="2026-08-10T10:00:10Z"),
        Event(event="payment.captured", payment_id="pay_008", order_id="order_008", ts="2026-08-10T10:00:10Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.ALREADY_RECOVERED
    assert result.recommended_action == RecommendedAction.STOP
    assert result.rule_id == "STATE-RULE-003"
    assert len(result.evidence_events) == 3


# 9. Invalid/missing payment ID
def test_missing_payment_id(engine):
    payment = PaymentRecord(payment_id="", order_id="order_009", amount=100)
    result = engine.evaluate_payment(payment, events=[])
    assert result.state == FinancialState.EXCEPTION
    assert result.recommended_action == RecommendedAction.ESCALATE
    assert result.rule_id == "STATE-RULE-000"


# 10. Out-of-order timestamps
def test_out_of_order_timestamps_sorted_correctly(engine):
    payment = PaymentRecord(payment_id="pay_010", order_id="order_010", amount=3000)
    events = [
        Event(event="payment.captured", payment_id="pay_010", order_id="order_010", ts="2026-08-10T10:05:00Z"),
        Event(event="payment.created", payment_id="pay_010", order_id="order_010", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_010", order_id="order_010", ts="2026-08-10T10:02:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.ALREADY_RECOVERED
    assert result.recommended_action == RecommendedAction.STOP
    assert result.rule_id == "STATE-RULE-003"
    assert result.evidence_events == ["payment.created", "payment.authorized", "payment.captured"]


# 11. Conflicting events (Captured then failed)
def test_conflicting_events_captured_then_failed(engine):
    payment = PaymentRecord(payment_id="pay_011", order_id="order_011", amount=4000)
    events = [
        Event(event="payment.created", payment_id="pay_011", order_id="order_011", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.captured", payment_id="pay_011", order_id="order_011", ts="2026-08-10T10:01:00Z"),
        Event(event="payment.failed", payment_id="pay_011", order_id="order_011", ts="2026-08-10T10:02:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.EXCEPTION
    assert result.recommended_action == RecommendedAction.ESCALATE
    assert result.rule_id == "STATE-RULE-000"
    assert "after payment was already captured" in result.reason


# 12. Hard permanent failure
def test_hard_permanent_failure(engine):
    payment = PaymentRecord(payment_id="pay_012", order_id="order_012", amount=899)
    events = [
        Event(event="payment.created", payment_id="pay_012", order_id="order_012", ts="2026-08-10T10:00:00Z"),
        Event(
            event="payment.failed",
            payment_id="pay_012",
            order_id="order_012",
            error_code="CARD_BLOCKED",
            error_description="Card blocked / reported lost",
            hardness="hard",
            ts="2026-08-10T10:00:06Z",
        ),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.VERIFIED_LOST
    assert result.recommended_action == RecommendedAction.EVALUATE_RECOVERY
    assert result.rule_id == "STATE-RULE-005"
    assert "CARD_BLOCKED" in result.reason


# 13. Late-auth flip-flop: FAILED -> PENDING -> AUTHORIZED -> CAPTURED
def test_late_auth_flip_flop_complex(engine):
    payment = PaymentRecord(payment_id="pay_013", order_id="order_013", amount=4999)
    events = [
        Event(event="payment.created", payment_id="pay_013", order_id="order_013", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_013", order_id="order_013", ts="2026-08-10T10:00:06Z"),
        Event(event="payment.pending", payment_id="pay_013", order_id="order_013", ts="2026-08-10T10:03:00Z"),
        Event(event="payment.authorized", payment_id="pay_013", order_id="order_013", ts="2026-08-10T10:05:00Z"),
        Event(event="payment.captured", payment_id="pay_013", order_id="order_013", ts="2026-08-10T10:06:00Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.ALREADY_RECOVERED
    assert result.recommended_action == RecommendedAction.STOP
    assert result.rule_id == "STATE-RULE-001"
    # Crucial: Verify RecoverAI does NOT recommend recovery
    assert result.recommended_action != RecommendedAction.EVALUATE_RECOVERY


# 14. Settlement mismatch exception
def test_settlement_mismatch_exception(engine):
    payment = PaymentRecord(
        payment_id="pay_014",
        order_id="order_014",
        amount=1999,
        has_settlement=True,
        settled_amount=1950.00,
        settlement_matches_order=False,
    )
    events = [
        Event(event="payment.created", payment_id="pay_014", order_id="order_014", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.authorized", payment_id="pay_014", order_id="order_014", ts="2026-08-10T10:00:08Z"),
        Event(event="payment.captured", payment_id="pay_014", order_id="order_014", ts="2026-08-10T10:00:12Z"),
    ]
    result = engine.evaluate_payment(payment, events=events)
    assert result.state == FinancialState.EXCEPTION
    assert result.recommended_action == RecommendedAction.ESCALATE
    assert result.rule_id == "STATE-RULE-000"
    assert "Settlement mismatch" in result.reason
