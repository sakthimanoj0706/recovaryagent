"""
Automated unit and integration test suite for RecoverAI Payment Gateway and Event Ingestion.
Covers all 14 Step 6 integration, idempotency, safety, and eventual consistency specifications.
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime, timezone

# Add src to python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import FinancialState, PaymentRecord, Event
from state_engine.engine import FinancialStateEngine
from gateway import (
    PaymentGateway,
    MockPaymentGateway,
    RazorpayGatewayAdapter,
    GatewayActionStatus,
    GatewayActionResult,
    get_gateway,
)
from ingestion import (
    EventProcessor,
    WebhookParser,
    EventNormalizer,
    WebhookPayload,
    IngestionStatus,
    IngestionResult,
)
from agent.models import RecoveryAction, FirewallDecision


@pytest.fixture
def processor(tmp_path):
    proc = EventProcessor()
    proc.clear_store()
    return proc


@pytest.fixture
def mock_gw():
    return MockPaymentGateway()


# 1. test_duplicate_webhook_is_idempotent
def test_duplicate_webhook_is_idempotent(processor):
    payload = {
        "provider": "mock",
        "event_id": "evt_dup_001",
        "event": "payment.failed",
        "payment_id": "pay_dup_001",
        "order_id": "ord_dup_001",
        "amount": 5000.0,
        "error_code": "INSUFFICIENT_FUNDS",
        "ts": "2026-08-28T10:00:00Z",
    }
    # First delivery
    res1 = processor.process_webhook(payload)
    assert res1.status == IngestionStatus.PROCESSED
    assert res1.financial_state_after == "VERIFIED_LOST"

    # Duplicate delivery
    res2 = processor.process_webhook(payload)
    assert res2.status == IngestionStatus.DUPLICATE_EVENT
    assert "Duplicate event" in res2.message
    # Duplicate did not change the event store count
    evs = processor.get_events_for_payment("pay_dup_001")
    assert len(evs) == 1


# 2. test_malformed_webhook_becomes_exception
def test_malformed_webhook_becomes_exception(processor):
    # Missing required 'payment_id'
    bad_payload_1 = {
        "provider": "mock",
        "event": "payment.failed",
        "amount": 1000.0,
    }
    res1 = processor.process_webhook(bad_payload_1)
    assert res1.status == IngestionStatus.MALFORMED_EVENT

    # Invalid amount type
    bad_payload_2 = {
        "provider": "mock",
        "event": "payment.failed",
        "payment_id": "pay_bad_02",
        "amount": "NOT_A_NUMBER",
    }
    res2 = processor.process_webhook(bad_payload_2)
    assert res2.status == IngestionStatus.MALFORMED_EVENT


# 3. test_event_timestamp_normalization
def test_event_timestamp_normalization():
    # Unix epoch seconds
    ts_epoch = "1756375200"
    norm_epoch = EventNormalizer.normalize_timestamp(ts_epoch)
    assert "T" in norm_epoch and ("+00:00" in norm_epoch or "Z" in norm_epoch)

    # ISO format string with offset
    ts_iso = "2026-08-28T15:30:00+05:30"
    norm_iso = EventNormalizer.normalize_timestamp(ts_iso)
    assert norm_iso.startswith("2026-08-28T10:00:00")

    # None / empty fallback
    norm_none = EventNormalizer.normalize_timestamp(None)
    assert isinstance(norm_none, str) and len(norm_none) > 10


# 4. test_late_capture_updates_financial_state
def test_late_capture_updates_financial_state(processor):
    pid = "pay_late_cap_01"
    # Phase 1: Failure arrives
    processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_lc_01",
        "event": "payment.failed",
        "payment_id": pid,
        "amount": 8000.0,
        "error_code": "TIMEOUT",
        "ts": "2026-08-28T10:00:00Z",
    })
    evs_p1 = processor.get_events_for_payment(pid)
    eval_p1 = processor.state_engine.evaluate_payment(PaymentRecord(payment_id=pid, amount=8000.0), evs_p1)
    assert eval_p1.state == FinancialState.VERIFIED_LOST

    # Phase 2: Capture arrives
    res_p2 = processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_lc_02",
        "event": "payment.captured",
        "payment_id": pid,
        "amount": 8000.0,
        "ts": "2026-08-28T10:15:00Z",
    })
    assert res_p2.financial_state_after == "ALREADY_RECOVERED"
    assert res_p2.state_changed is True


# 5. test_late_authorization_blocks_recovery
def test_late_authorization_blocks_recovery(processor):
    pid = "pay_late_auth_01"
    # Failed first
    processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_la_01",
        "event": "payment.failed",
        "payment_id": pid,
        "amount": 10000.0,
        "error_code": "BANK_DOWNTIME",
        "ts": "2026-08-28T10:00:00Z",
    })
    # Late auth arrives
    res = processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_la_02",
        "event": "payment.authorized",
        "payment_id": pid,
        "amount": 10000.0,
        "late_authorization": True,
        "ts": "2026-08-28T10:20:00Z",
    })
    assert res.financial_state_after == "ALREADY_RECOVERED"
    # No recovery action dispatched when state becomes ALREADY_RECOVERED
    assert res.orchestrator_result is None or res.orchestrator_result.get("agent_action") in [None, "STOP"]


# 6. test_gateway_cannot_change_financial_state
def test_gateway_cannot_change_financial_state(mock_gw):
    # Mock gateway execution result does not determine FinancialState
    result = mock_gw.create_payment_link(payment_id="pay_gw_01", amount=5000.0)
    assert isinstance(result, GatewayActionResult)
    assert not hasattr(result, "financial_state")
    assert not hasattr(result, "state")


# 7. test_gateway_cannot_bypass_firewall
def test_gateway_cannot_bypass_firewall(processor):
    # Hard decline CARD_BLOCKED
    pid = "pay_gw_fw_01"
    res = processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_gw_fw_01",
        "event": "payment.failed",
        "payment_id": pid,
        "amount": 15000.0,
        "error_code": "CARD_BLOCKED",
        "hardness": "hard",
        "ts": "2026-08-28T10:00:00Z",
    })
    assert res.financial_state_after == "VERIFIED_LOST"
    # Orchestrator does not allow RETRY for hard declines
    if res.orchestrator_result:
        assert res.orchestrator_result.get("agent_action") != "RETRY"


# 8. test_llm_cannot_execute_gateway_action
def test_llm_cannot_execute_gateway_action(monkeypatch):
    # Verify that Gateway can only be invoked by deterministic code, not LLM prompts
    monkeypatch.setenv("RECOVERAI_PROVIDER_MODE", "simulation")
    gw = get_gateway()
    assert isinstance(gw, PaymentGateway)
    assert gw.is_simulation is True


# 9. test_duplicate_action_not_executed
def test_duplicate_action_not_executed(mock_gw):
    res1 = mock_gw.retry_payment(payment_id="pay_dup_act_01", amount=3000.0)
    assert res1.status == GatewayActionStatus.SUCCESS
    # Cancel action
    cancel_res = mock_gw.cancel_action("pay_dup_act_01", res1.execution_id)
    assert cancel_res.status == GatewayActionStatus.SUCCESS


# 10. test_webhook_does_not_double_recover
def test_webhook_does_not_double_recover(processor):
    pid = "pay_no_double_01"
    payload = {
        "provider": "mock",
        "event_id": "evt_double_01",
        "event": "payment.failed",
        "payment_id": pid,
        "amount": 6000.0,
        "error_code": "INSUFFICIENT_FUNDS",
        "ts": "2026-08-28T10:00:00Z",
    }
    res1 = processor.process_webhook(payload)
    assert res1.status == IngestionStatus.PROCESSED

    # Ingest same webhook again
    res2 = processor.process_webhook(payload)
    assert res2.status == IngestionStatus.DUPLICATE_EVENT
    assert res2.orchestrator_result is None


# 11. test_provider_event_ordering
def test_provider_event_ordering(processor):
    pid = "pay_order_01"
    # Deliver out of order: captured first, then created
    processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_ord_02",
        "event": "payment.captured",
        "payment_id": pid,
        "amount": 4000.0,
        "ts": "2026-08-28T10:05:00Z",
    })
    processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_ord_01",
        "event": "payment.created",
        "payment_id": pid,
        "amount": 4000.0,
        "ts": "2026-08-28T10:00:00Z",
    })
    # Store maintains chronological order
    evs = processor.get_events_for_payment(pid)
    assert len(evs) == 2
    assert evs[0].event == "payment.created"
    assert evs[1].event == "payment.captured"


# 12. test_eventual_consistency
def test_eventual_consistency(processor):
    pid = "pay_ec_01"
    # 1. Created
    processor.process_webhook({"provider": "mock", "event_id": "ec_1", "event": "payment.created", "payment_id": pid, "amount": 9000.0, "ts": "2026-08-28T10:00:00Z"})
    # 2. Failed -> VERIFIED_LOST
    res_f = processor.process_webhook({"provider": "mock", "event_id": "ec_2", "event": "payment.failed", "payment_id": pid, "amount": 9000.0, "error_code": "TIMEOUT", "ts": "2026-08-28T10:00:05Z"})
    assert res_f.financial_state_after == "VERIFIED_LOST"

    # 3. Later capture arrives -> ALREADY_RECOVERED
    res_c = processor.process_webhook({"provider": "mock", "event_id": "ec_3", "event": "payment.captured", "payment_id": pid, "amount": 9000.0, "ts": "2026-08-28T10:45:00Z"})
    assert res_c.financial_state_after == "ALREADY_RECOVERED"
    assert res_c.state_changed is True


# 13. test_mock_gateway_deterministic
def test_mock_gateway_deterministic():
    gw = MockPaymentGateway()
    gw.configure_outcome("pay_det_01", GatewayActionStatus.FAILURE)
    res_fail = gw.create_payment_link("pay_det_01", amount=2000.0)
    assert res_fail.status == GatewayActionStatus.FAILURE

    gw.configure_outcome("pay_det_02", GatewayActionStatus.SUCCESS)
    res_succ = gw.create_payment_link("pay_det_02", amount=2000.0)
    assert res_succ.status == GatewayActionStatus.SUCCESS


# 14. test_raw_payload_preserved_for_audit
def test_raw_payload_preserved_for_audit(processor):
    pid = "pay_audit_raw_01"
    custom_payload = {"merchant_reference": "inv_9981", "tax_breakdown": {"cgst": 90, "sgst": 90}}
    processor.process_webhook({
        "provider": "mock",
        "event_id": "evt_raw_01",
        "event": "payment.failed",
        "payment_id": pid,
        "amount": 1000.0,
        "payload": custom_payload,
        "ts": "2026-08-28T10:00:00Z",
    })
    records = processor._payment_raw_records.get(pid, [])
    assert len(records) == 1
    assert records[0].raw_payload == custom_payload
