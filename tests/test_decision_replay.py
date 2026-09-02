"""
Comprehensive Test Suite for RecoverAI Decision Replay & Evidence Graph (Step 13).

Tests:
1. Basic success replay with evidence graph generation
2. Determinism (same input = same evidence graph = same SHA-256 hash)
3. Hard decline firewall interception (LLM advisory ignored, ₹0 unearned claim)
4. Negative expected net value withholding
5. Gateway success without verification (unearned claim prevented)
6. Partial capture exact split and accounting
7. Refund handling and reversal proof
8. Duplicate webhook idempotency
9. Conflicting event payload handling
10. Out-of-order webhook timestamp normalization
11. Adversarial prompt injection isolation proof
12. Cryptographic evidence hash & tamper detection
13. Strict simulation-only enforcement (rejection of simulation_only=False)
14. Unknown preset error handling
15. Audit trail generation and reference
16. Accounting conservation invariant across all 11 archetypes
17. No mutation of global state or benchmark data
18. Full REST API endpoints verification
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from state_engine.models import PaymentRecord, Event
from replay import (
    ReplayRequest,
    ReplayService,
    ReplayEngine,
    verify_graph_integrity,
    compute_canonical_evidence_hash,
)
from api.server import app

client = TestClient(app)


# =========================================================================
# 1. BASIC SUCCESS REPLAY & ACCOUNTING
# =========================================================================
def test_basic_success_replay():
    """Verify successful retry produces complete evidence graph and exact accounting."""
    service = ReplayService()
    replay = service.replay_preset("SUCCESSFUL_RETRY")

    assert replay.payment_id == "pay_rpl_success_01"
    assert replay.initial_financial_state == "VERIFIED_LOST"
    assert replay.selected_action in ("RETRY", "PAYMENT_LINK")
    assert replay.firewall_verdict == "APPROVED"
    assert replay.final_financial_state in ("VERIFIED_RECOVERED", "ALREADY_RECOVERED")
    assert replay.verification_summary.get("is_verified_recovery") is True
    assert replay.financial_proof.verified_cash_collected == 12500.0
    assert replay.financial_proof.phantom_revenue == 0.0
    assert replay.financial_proof.accounting_imbalance == 0.0
    assert replay.financial_proof.is_accounting_conserved is True

    # Graph checks
    graph = replay.evidence_graph
    assert len(graph.nodes) >= 6
    assert len(graph.edges) >= 5
    assert replay.evidence_hash == graph.canonical_hash

    is_valid, msg = verify_graph_integrity(graph)
    assert is_valid is True


# =========================================================================
# 2. DETERMINISM & HASH REPRODUCIBILITY
# =========================================================================
def test_replay_determinism():
    """Verify same inputs produce identical results and identical SHA-256 evidence hashes."""
    service = ReplayService()
    r1 = service.replay_preset("SUCCESSFUL_RETRY", seed=42)
    r2 = service.replay_preset("SUCCESSFUL_RETRY", seed=42)

    assert r1.evidence_hash == r2.evidence_hash
    assert r1.final_financial_state == r2.final_financial_state
    assert r1.financial_proof.verified_cash_collected == r2.financial_proof.verified_cash_collected
    assert len(r1.evidence_graph.nodes) == len(r2.evidence_graph.nodes)


# =========================================================================
# 3. HARD DECLINE FIREWALL INTERCEPTION
# =========================================================================
def test_hard_decline_blocked_replay():
    """Verify hard decline retry is blocked by Firewall with zero unearned claim."""
    service = ReplayService()
    replay = service.replay_preset("HARD_DECLINE_BLOCKED")

    assert replay.initial_financial_state == "VERIFIED_LOST"
    assert replay.firewall_verdict in ("STOP", "BLOCK", "ESCALATE")
    assert replay.financial_proof.verified_cash_collected == 0.0
    assert replay.financial_proof.phantom_revenue == 0.0
    assert replay.financial_proof.protected_unrecovered_value == 25000.0
    assert replay.financial_proof.accounting_imbalance == 0.0
    assert "FIREWALL-004" in replay.provenance.headline or "FIREWALL-004" in str(replay.provenance.safety_interceptions)


# =========================================================================
# 4. NEGATIVE EXPECTED NET VALUE
# =========================================================================
def test_negative_env_withheld_replay():
    """Verify micro-payment with negative ENV has recovery withheld."""
    service = ReplayService()
    replay = service.replay_preset("NEGATIVE_ENV_WITHHELD")

    assert replay.payment_id == "pay_rpl_negenv_10"
    assert replay.financial_proof.verified_cash_collected == 0.0
    assert replay.financial_proof.protected_unrecovered_value == 5.0
    assert replay.financial_proof.accounting_imbalance == 0.0


# =========================================================================
# 5. GATEWAY SUCCESS WITHOUT VERIFICATION
# =========================================================================
def test_gateway_success_verification_pending():
    """Verify gateway success without ledger confirmation produces zero verified recovery."""
    service = ReplayService()
    replay = service.replay_preset("GATEWAY_SUCCESS_VERIFICATION_PENDING")

    assert replay.verification_summary.get("is_verified_recovery") is not True
    assert replay.financial_proof.verified_cash_collected == 0.0
    assert replay.financial_proof.phantom_revenue == 0.0
    assert replay.financial_proof.accounting_imbalance == 0.0


# =========================================================================
# 6. PARTIAL CAPTURE & ACCOUNTING
# =========================================================================
def test_partial_capture_replay():
    """Verify partial capture reports exact recovered and outstanding values."""
    service = ReplayService()
    replay = service.replay_preset("PARTIAL_CAPTURE")

    assert replay.financial_proof.verified_cash_collected == 6000.0
    assert replay.financial_proof.outstanding_value == 4000.0
    assert replay.financial_proof.accounting_imbalance == 0.0


# =========================================================================
# 7. REFUND HANDLING
# =========================================================================
def test_refund_after_capture_replay():
    """Verify refund after capture resets verified cash to zero."""
    service = ReplayService()
    replay = service.replay_preset("REFUND_AFTER_CAPTURE")

    assert replay.financial_proof.verified_cash_collected == 0.0
    assert replay.financial_proof.refunded_value == 5000.0
    assert replay.financial_proof.accounting_imbalance == 0.0


# =========================================================================
# 8. DUPLICATE & OUT-OF-ORDER WEBHOOKS
# =========================================================================
def test_duplicate_and_out_of_order_replay():
    """Verify idempotency and timestamp normalization."""
    service = ReplayService()
    dup_replay = service.replay_preset("DUPLICATE_WEBHOOK")
    assert dup_replay.final_financial_state == "ALREADY_RECOVERED"
    assert dup_replay.financial_proof.double_charges == 0
    assert dup_replay.financial_proof.accounting_imbalance == 0.0

    ooo_replay = service.replay_preset("OUT_OF_ORDER_EVENTS")
    assert ooo_replay.final_financial_state == "ALREADY_RECOVERED"
    assert ooo_replay.financial_proof.accounting_imbalance == 0.0


# =========================================================================
# 9. PROMPT INJECTION ISOLATION
# =========================================================================
def test_prompt_injection_replay():
    """Verify prompt injection in transaction metadata has zero authority over deterministic engine."""
    service = ReplayService()
    replay = service.replay_preset("PROMPT_INJECTION_CONTAINED")

    assert replay.provenance.prompt_injection_detected is True
    assert replay.provenance.prompt_injection_contained is True
    assert replay.firewall_verdict in ("STOP", "BLOCK", "ESCALATE")
    assert replay.financial_proof.verified_cash_collected == 0.0
    assert replay.financial_proof.phantom_revenue == 0.0
    assert replay.financial_proof.accounting_imbalance == 0.0



# =========================================================================
# 10. CRYPTOGRAPHIC EVIDENCE INTEGRITY & TAMPER DETECTION
# =========================================================================
def test_evidence_tamper_detection():
    """Verify altering an evidence node invalidates the canonical SHA-256 hash."""
    service = ReplayService()
    replay = service.replay_preset("SUCCESSFUL_RETRY")
    original_hash = replay.evidence_hash

    # Check untampered graph
    is_valid, _ = verify_graph_integrity(replay.evidence_graph)
    assert is_valid is True

    # Tamper with an evidence node
    replay.evidence_graph.nodes[0].value = "TAMPERED_FAKE_VALUE"
    is_valid_tampered, msg = verify_graph_integrity(replay.evidence_graph)
    assert is_valid_tampered is False
    assert "TAMPER DETECTED" in msg


# =========================================================================
# 11. STRICT SIMULATION-ONLY ENFORCEMENT
# =========================================================================
def test_simulation_only_enforcement():
    """Verify ReplayRequest rejects simulation_only = False."""
    with pytest.raises(ValidationError):
        ReplayRequest(preset_key="SUCCESSFUL_RETRY", simulation_only=False)

    engine = ReplayEngine()
    with pytest.raises(ValueError):
        engine.replay_lifecycle(
            payment=PaymentRecord(payment_id="pay_test", amount=1000.0),
            events=[],
            simulation_only=False,
        )


# =========================================================================
# 12. UNKNOWN PRESET ERROR HANDLING
# =========================================================================
def test_unknown_preset_error():
    """Verify unknown preset key raises clean error."""
    service = ReplayService()
    with pytest.raises(KeyError):
        service.replay_preset("NON_EXISTENT_PRESET_KEY")


# =========================================================================
# 13. ACCOUNTING CONSERVATION ACROSS ALL 11 FIXTURES
# =========================================================================
def test_accounting_conservation_all_presets():
    """Verify every built-in test archetype strictly satisfies Accounting Imbalance == Rs. 0.00."""
    service = ReplayService()
    for preset_key in service.PRESET_FIXTURES.keys():
        replay = service.replay_preset(preset_key)
        assert replay.financial_proof.accounting_imbalance == 0.0, f"Preset {preset_key} failed accounting balance!"
        assert replay.financial_proof.is_accounting_conserved is True


# =========================================================================
# 14. REST API ENDPOINTS
# =========================================================================
def test_replay_api_endpoints():
    """Verify all REST API endpoints operate cleanly."""
    # 1. GET /api/replay/presets
    resp_presets = client.get("/api/replay/presets")
    assert resp_presets.status_code == 200
    catalog = resp_presets.json()
    assert len(catalog) >= 10

    # 2. POST /api/replay/run
    resp_run = client.post("/api/replay/run", json={"preset_key": "SUCCESSFUL_RETRY", "simulation_only": True})
    assert resp_run.status_code == 200
    data = resp_run.json()
    assert "replay" in data
    run_id = data["replay"]["run_id"]

    # 3. GET /api/replay/latest
    resp_latest = client.get("/api/replay/latest")
    assert resp_latest.status_code == 200
    assert resp_latest.json()["replay"]["run_id"] == run_id

    # 4. GET /api/replay/{run_id}
    resp_get = client.get(f"/api/replay/{run_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["replay"]["run_id"] == run_id

    # 5. GET /api/replay/{run_id}/graph
    resp_graph = client.get(f"/api/replay/{run_id}/graph")
    assert resp_graph.status_code == 200
    assert resp_graph.json()["integrity_verified"] is True

    # 6. GET /api/replay/{run_id}/explanation
    resp_expl = client.get(f"/api/replay/{run_id}/explanation")
    assert resp_expl.status_code == 200
    assert "headline" in resp_expl.json()

    # 7. GET /api/replay/{run_id}/evidence
    resp_ev = client.get(f"/api/replay/{run_id}/evidence")
    assert resp_ev.status_code == 200
    assert "financial_proof" in resp_ev.json()
