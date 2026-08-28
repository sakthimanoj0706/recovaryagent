# RecoverAI — Step 7: Production-Grade Observability, Reliability & Demo Hardening

## 1. Executive Summary & Core Invariant

RecoverAI is built upon a single non-negotiable financial principle:

> **"RecoverAI is not an LLM that controls payments. It is a bounded financial agent operating inside deterministic financial safety rails."**

All financial decisions follow an immutable 7-stage pipeline:

$$\text{OBSERVED} \longrightarrow \text{PROVEN} \longrightarrow \text{EXPLAINED} \longrightarrow \text{GUARDED} \longrightarrow \text{EXECUTED} \longrightarrow \text{VERIFIED} \longrightarrow \text{AUDITED}$$

---

## 2. Architecture & Subsystem Topology

```
                    PAYMENT EVENTS (Webhooks / Real-Time Streams)
                                     |
                                     v
                        EVENT INGESTION PIPELINE
                     (Parse -> Normalize -> Deduplicate)
                                     |
                                     v
                           FINANCIAL STATE ENGINE
                                  [PROVE]
                                     |
                  +------------------+------------------+
                  |                                     |
            NOT VERIFIED_LOST                     VERIFIED_LOST
                  |                                     |
            HALT / WAIT /                     RECOVERY INTELLIGENCE
              ESCALATE                             [PRIORITIZE]
                                                        |
                                                 AGENTIC PLANNER
                                                     [PLAN]
                                                        |
                                                 POLICY ENGINE
                                                        |
                                               RECOVERY FIREWALL
                                                    [GUARD]
                                                        |
                                                PAYMENT GATEWAY
                                                     [ACT]
                                                        |
                                                 EVENT STREAM
                                                        |
                                               FINANCIAL STATE ENGINE
                                                    [VERIFY]
                                                        |
                                                  AUDIT TRAIL
```

---

## 3. Correlation ID (`run_id`) Design

Every recovery attempt is assigned an immutable `run_id` (e.g. `run_8f319a2b7c`) that correlates all operations across:
1. Webhook Ingestion (`IngestionResult.run_id`)
2. Event Store records (`IngestedEventRecord.run_id`)
3. Financial State Engine evaluation
4. Recovery Intelligence ML prediction
5. Advisory Agent proposal & Policy checks
6. Deterministic Firewall gate evaluation
7. Gateway action dispatch
8. Independent Verification & Ledger State
9. Immutable JSONL Audit Trail & UI timeline

---

## 4. Structured Audit Event Schema

Granular stage events are recorded to an append-only JSONL ledger (`logs/recovery_structured_events.jsonl`):

```json
{
  "timestamp": "2026-08-28T14:00:03.120Z",
  "run_id": "run_8f319a2b7c",
  "payment_id": "pay_30k_example",
  "order_id": "ord_30k_example",
  "stage": "GUARD",
  "component": "RecoveryFirewall",
  "event_type": "FIREWALL_EVALUATION",
  "decision": "APPROVED",
  "reason": "All deterministic safety rules passed. Action within limits.",
  "rule_id": "PASSED",
  "financial_state": "VERIFIED_LOST",
  "agent_action": "PAYMENT_LINK",
  "execution_status": "PENDING",
  "verification_state": "VERIFIED_LOST",
  "simulation_flag": true,
  "metadata": {"retry_count": 0, "env": 27981.49}
}
```

Stages: `OBSERVE`, `PROVE`, `PRIORITIZE`, `PLAN`, `POLICY`, `GUARD`, `ACT`, `VERIFY`, `STOP`.

---

## 5. System Health & Readiness API

### `GET /api/system/health`
Returns live operational state of all 9 subsystems:
- `status`: `"HEALTHY"`
- `version`: `"1.0.0"`
- `simulation_mode`: `true`
- `demo_mode`: `true`
- `model_loaded`: `true`
- `gateway_mode`: `"mock"`
- `event_store_status`: `"ACTIVE"`
- `audit_status`: `"APPEND_ONLY"`

### `GET /api/system/ready`
Readiness probe verifying core engine, ML model, firewall, gateway, and append-only storage.
- Returns `status`: `"HEALTHY"`, `"DEGRADED"`, or `"NOT_READY"`.

---

## 6. Failure Injection & Chaos Validation (`validate_failure_injection.py`)

Six deterministic failure scenarios validated with 100% safety:
1. **Gateway Timeout**: Handled safely without emitting false recovery events.
2. **Duplicate Webhook**: Intercepted as `DUPLICATE_EVENT` with zero double execution.
3. **Planner Service Outage**: Gracefully falls back to `ESCALATE` (FIREWALL-010).
4. **Verification Mismatch**: Verifier independently catches failed recovery and forces `RECOVERY_FAILED`.
5. **Negative ENV**: Economically irrational recovery withheld via `FIREWALL-002`.
6. **Hard Decline Direct Retry**: Automated retry blocked via `FIREWALL-004`.

---

## 7. Boundary Idempotency

Idempotency is enforced at all key integration boundaries:
- **Webhook Boundary**: Deduplicated by `(provider, event_id)`.
- **Gateway Action Boundary**: Deduplicated by `(payment_id, action)`.
- **Retry Count Boundary**: Hard limit enforced by `FIREWALL-005` ($N \ge 3$).
- **Ledger Verification Boundary**: Once `ALREADY_RECOVERED`, all further recovery is blocked.

---

## 8. Accounting Buckets & Invariant Balance

The system guarantees the fundamental financial accounting invariant:

$$\text{processed\_amount} = \text{amount\_recovered} + \text{amount\_withheld} + \text{amount\_pending} + \text{amount\_escalated}$$

Metrics recorded in `SystemMetrics`:
- `total_amount_recovered`: Confirmed collected funds.
- `total_amount_withheld`: Saved capital protected by safety stops or $-EV$.
- `total_amount_pending`: Funds in-flight awaiting settlement window.
- `total_amount_escalated`: Mismatches routed to human operations.

---

## 9. Demo Snapshot / Deterministic Offline Mode

When `DEMO_MODE=true` is set:
- Deterministic mock gateway is utilized.
- External API dependencies (Gemini/OpenRouter) fail safely to deterministic policies.
- UI explicitly displays `SIMULATION MODE` / `DEMO MODE` / `NO REAL TRANSACTIONS`.

---

## 10. Adversarial Test Results (`tests/test_adversarial.py`)

**15 / 15 adversarial tests passed** covering:
- Late authorization after recovery action
- Capture arriving 8 hours after failure
- Duplicate capture idempotency
- Impossible state transitions (failed after captured, refunded without captured)
- Malformed webhook rejection
- Duplicate recovery request block
- Hallucinated LLM action rejection
- Prohibited retry on hard decline
- High-value hard decline block
- Negative ENV withholding
- Max retry limit exhaustion
- Verifier vs Executor disagreement
- Gateway success vs Ledger failure

---

## 11. Test & Scenario Summary

- **Total Automated Pytest Tests**: **142 / 142 Passing (100%)**
  - `tests/test_adversarial.py`: 15 tests
  - `tests/test_gateway_ingestion.py`: 14 tests
  - `tests/test_agentic_orchestrator.py`: 15 tests
  - `tests/test_agent.py`: 20 tests
  - `tests/test_agent_orchestrator.py`: 17 tests
  - `tests/test_agent_trace.py`: 11 tests
  - `tests/test_closed_loop.py`: 14 tests
  - `tests/test_execution.py`: 5 tests
  - `tests/test_recovery.py`: 14 tests
  - `tests/test_state_engine.py`: 17 tests

- **Validation Suites**: **100% Passing**
  - `validate_e2e_5_scenarios.py` (Scenarios 1–5: Pass)
  - `validate_e2e_5_scenarios_batch2.py` (Scenarios 6–10: Pass)
  - `validate_e2e_5_scenarios_batch3.py` (Scenarios 11–15: Pass)
  - `validate_agentic_demo.py` (Pass)
  - `demo_live_event_loop.py` (Pass)
  - `validate_failure_injection.py` (Pass)
  - `demo_full_system.py` (Pass)

---

## 12. Live Demo Instructions

To run the complete RecoverAI master demo in one command:

```bash
python demo_full_system.py
```

To run the controlled failure injection suite:

```bash
python validate_failure_injection.py
```

To run the real-time asynchronous event simulator:

```bash
python simulate_event_stream.py
```

---

## 13. Judge FAQ

**Q: Does the LLM have direct access to execute payment refunds or retries?**  
**A:** No. The LLM is an advisory-only component. Only deterministic Python code passing the `RecoveryFirewall` can trigger gateway operations.

**Q: What happens if a customer pays via a second tab while the agent is planning?**  
**A:** When `payment.captured` or `payment.authorized` arrives, the `FinancialStateEngine` transitions the state to `ALREADY_RECOVERED`. `FIREWALL-006` immediately halts all recovery actions and prevents double recovery.

**Q: Are real bank rails triggered?**  
**A:** No. All gateway operations run strictly in `SIMULATION MODE`.
