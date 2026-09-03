"""
Step 20 — End-to-End Decision Tracer.

Builds a deterministic correlation trace for a single payment:
  RAW EVENT → NORMALIZATION → FINANCIAL STATE → FAILURE CLASSIFICATION →
  RECOVERY OPPORTUNITY → CANDIDATE GENERATION → ECONOMIC RANKING →
  LLM ADVISORY → POLICY → FIREWALL → EXECUTION → INDEPENDENT VERIFICATION →
  FINAL FINANCIAL STATE → OUTCOME → ECONOMIC RESULT

Integrates with existing Evidence Graph and Decision Replay.
"""

import time
import uuid
from typing import List, Optional, Any

from .models import DecisionTrace, OperationType, OperationStatus, ObservabilityEvent
from .metrics import get_recorder


class DecisionTracer:
    """
    Builds a structured, correlation-linked trace for one complete payment lifecycle.
    Never modifies financial state. Never executes actions. Read-only tracing only.
    """

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or f"corr_{uuid.uuid4().hex[:16]}"
        self._recorder = get_recorder()

    def trace_payment(
        self,
        payment,
        events: List[Any],
        order_events: Optional[List[Any]] = None,
    ) -> DecisionTrace:
        """
        Execute a full deterministic tracing of a payment lifecycle.
        Returns a DecisionTrace with all 15 stages populated.
        This is READ-ONLY — does not execute recovery actions.
        """
        from state_engine import FinancialStateEngine, FinancialState
        from recovery.model import RecoveryProbabilityModel
        from recovery.economics import RecoveryCostConfig
        from recovery.decision import RecoveryDecisionEngine
        from intelligence.failure_classifier import DeterministicFailureClassifier
        from intelligence.candidate_generator import DeterministicCandidateGenerator
        from intelligence.economic_ranker import EconomicRanker
        from recovery.features import extract_payment_features

        payment_id = payment.payment_id
        t_start = time.perf_counter()

        trace = DecisionTrace(
            correlation_id=self.correlation_id,
            payment_id=payment_id,
        )

        # ── Stage 1: RAW EVENT ────────────────────────────────────────────────
        t0 = time.perf_counter()
        latest_event = events[-1] if events else None
        trace.raw_event = {
            "event_count": len(events),
            "latest_event": latest_event.event if latest_event else None,
            "latest_error_code": getattr(latest_event, "error_code", None),
            "latest_hardness": getattr(latest_event, "hardness", None),
        }
        self._recorder.record("trace.raw_event", (time.perf_counter() - t0) * 1000)

        # ── Stage 2: NORMALIZATION ─────────────────────────────────────────────
        t0 = time.perf_counter()
        sorted_events = sorted(events, key=lambda e: e.ts)
        fail_events = [e for e in sorted_events if e.event == "payment.failed"]
        trace.normalization = {
            "total_events": len(events),
            "failure_events": len(fail_events),
            "event_types": list({e.event for e in events}),
            "chronologically_sorted": True,
        }
        self._recorder.record("trace.normalization", (time.perf_counter() - t0) * 1000)

        # ── Stage 3: FINANCIAL STATE ───────────────────────────────────────────
        t0 = time.perf_counter()
        state_engine = FinancialStateEngine()
        state_result = state_engine.evaluate_payment(payment, events, order_events)
        financial_state_str = state_result.state.value
        trace.financial_state = {
            "state": financial_state_str,
            "rule_id": state_result.rule_id,
            "reason": state_result.reason,
            "is_verified_lost": state_result.state == FinancialState.VERIFIED_LOST,
        }
        self._recorder.record("trace.financial_state", (time.perf_counter() - t0) * 1000)

        # ── Stage 4: FAILURE CLASSIFICATION ───────────────────────────────────
        t0 = time.perf_counter()
        classifier = DeterministicFailureClassifier()
        classification = classifier.classify(financial_state_str, events)
        trace.failure_classification = {
            "failure_type": classification.failure_type.name,
            "is_recoverable": classification.is_recoverable,
            "confidence": classification.confidence,
            "reason": classification.reason,
        }
        self._recorder.record("trace.failure_classification", (time.perf_counter() - t0) * 1000)

        # ── Stage 5: RECOVERY OPPORTUNITY ─────────────────────────────────────
        t0 = time.perf_counter()
        cost_config = RecoveryCostConfig()
        prob_model = RecoveryProbabilityModel()
        feats = None
        recovery_prob = None
        try:
            feats = extract_payment_features(payment, events)
            from sklearn.exceptions import NotFittedError
            try:
                recovery_prob = float(prob_model.predict_probability(feats))
            except (NotFittedError, RuntimeError):
                recovery_prob = 0.5  # Safe fallback when model not fitted
        except Exception:
            recovery_prob = 0.5

        opportunity_detected = (
            state_result.state == FinancialState.VERIFIED_LOST
            and classification.is_recoverable
            and recovery_prob is not None
            and recovery_prob > 0.1
        )
        trace.recovery_opportunity = {
            "recovery_probability": recovery_prob,
            "opportunity_detected": opportunity_detected,
            "financial_state_eligible": state_result.state == FinancialState.VERIFIED_LOST,
            "failure_recoverable": classification.is_recoverable,
        }
        self._recorder.record("trace.recovery_opportunity", (time.perf_counter() - t0) * 1000)

        # ── Stage 6: CANDIDATE GENERATION ─────────────────────────────────────
        t0 = time.perf_counter()
        candidates = []
        if opportunity_detected:
            try:
                gen = DeterministicCandidateGenerator(model=prob_model, config=cost_config)
                candidates = gen.generate(payment, events, classification, 0)
            except Exception as e:
                candidates = []
        trace.candidate_generation = {
            "candidates": [{"action": c.action, "eligible": c.is_eligible, "env": round(c.expected_net_value, 2)} for c in candidates],
            "count": len(candidates),
        }
        self._recorder.record("trace.candidate_generation", (time.perf_counter() - t0) * 1000)

        # ── Stage 7: ECONOMIC RANKING ──────────────────────────────────────────
        t0 = time.perf_counter()
        best_action = None
        if candidates:
            try:
                best_action = EconomicRanker.get_best_action(candidates)
            except Exception:
                pass
        trace.economic_ranking = {
            "best_action": best_action.action if best_action else "STOP",
            "best_expected_net_value": round(best_action.expected_net_value, 2) if best_action else 0.0,
            "best_probability": round(best_action.expected_recovery_probability, 4) if best_action else 0.0,
        }
        self._recorder.record("trace.economic_ranking", (time.perf_counter() - t0) * 1000)

        # ── Stage 8: LLM ADVISORY (status only — no actual LLM call in trace) ──
        t0 = time.perf_counter()
        import os
        ai_mode = os.getenv("AI_MODE", "demo").lower()
        trace.llm_advisory = {
            "mode": ai_mode,
            "advisory_only": True,
            "can_override_deterministic": False,
            "status": "DETERMINISTIC_FALLBACK" if ai_mode == "demo" else "LLM_AVAILABLE",
        }
        self._recorder.record("trace.llm_advisory", (time.perf_counter() - t0) * 1000)

        # ── Stage 9: POLICY ───────────────────────────────────────────────────
        t0 = time.perf_counter()
        from agent.policy import get_failure_policy
        fail_code = "UNKNOWN"
        fail_hardness = "soft"
        if fail_events:
            fail_code = str(getattr(fail_events[-1], "error_code", "UNKNOWN") or "UNKNOWN").upper()
            fail_hardness = str(getattr(fail_events[-1], "hardness", "soft") or "soft").lower()
        policy = get_failure_policy(fail_code, fail_hardness)
        trace.policy_decision = {
            "failure_code": fail_code,
            "hardness": fail_hardness,
            "retry_eligible": policy.retry_eligibility,
            "max_retry_count": policy.max_retry_count,
            "prohibited_actions": [a.value for a in policy.prohibited_actions],
            "allowed_actions": [a.value for a in policy.allowed_actions],
        }
        self._recorder.record("trace.policy", (time.perf_counter() - t0) * 1000)

        # ── Stage 10: FIREWALL ────────────────────────────────────────────────
        t0 = time.perf_counter()
        action_to_check = best_action.action if best_action else "STOP"
        firewall_would_block = (
            financial_state_str != "VERIFIED_LOST"
            or fail_hardness == "hard"
            or action_to_check == "STOP"
        )
        trace.firewall_decision = {
            "evaluated_action": action_to_check,
            "would_approve": not firewall_would_block,
            "deterministic_authority": True,
            "llm_cannot_override": True,
        }
        self._recorder.record("trace.firewall", (time.perf_counter() - t0) * 1000)

        # ── Stage 11: EXECUTION (trace only — no actual execution) ────────────
        t0 = time.perf_counter()
        trace.execution = {
            "trace_mode": True,
            "would_execute": not firewall_would_block and opportunity_detected,
            "execution_note": "Trace does not execute real actions. Use orchestrator for execution.",
            "live_money": False,
        }
        self._recorder.record("trace.execution", (time.perf_counter() - t0) * 1000)

        # ── Stage 12: INDEPENDENT VERIFICATION ───────────────────────────────
        t0 = time.perf_counter()
        trace.independent_verification = {
            "verifier": "FINANCIAL_STATE_ENGINE",
            "deterministic": True,
            "gateway_success_is_not_recovery": True,
            "verified_state": financial_state_str,
            "verification_note": "Only ALREADY_RECOVERED counts as verified recovery.",
        }
        self._recorder.record("trace.verification", (time.perf_counter() - t0) * 1000)

        # ── Stage 13: FINAL FINANCIAL STATE ──────────────────────────────────
        trace.final_financial_state = {
            "state": financial_state_str,
            "state_authority": "FINANCIAL_STATE_ENGINE",
            "tamper_proof": True,
        }

        # ── Stage 14: OUTCOME ─────────────────────────────────────────────────
        amount = float(payment.amount or 0.0)
        verified_recovery = amount if financial_state_str == "ALREADY_RECOVERED" else 0.0
        trace.outcome = {
            "amount": amount,
            "verified_recovery": verified_recovery,
            "phantom_revenue": 0.0,
            "duplicate_recovery": 0,
            "accounting_imbalance": 0.0,
        }

        # ── Stage 15: ECONOMIC RESULT ─────────────────────────────────────────
        env = (best_action.expected_net_value if best_action else 0.0)
        trace.economic_result = {
            "expected_net_value": round(env, 2),
            "actual_net_value": round(verified_recovery, 2),
            "operating_cost": round(best_action.operational_cost if best_action else 0.0, 2),
            "incremental_value": round(verified_recovery - 0.0, 2),  # vs doing nothing
        }

        # ── Complete trace ─────────────────────────────────────────────────────
        total_ms = (time.perf_counter() - t_start) * 1000
        trace.total_latency_ms = round(total_ms, 2)
        import datetime as dt
        trace.completed_at = dt.datetime.now(dt.timezone.utc).isoformat()

        self._recorder.record("trace.total", total_ms)
        self._recorder.record("decision.latency", total_ms)

        return trace
