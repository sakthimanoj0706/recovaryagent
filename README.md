# RecoverAI
> **AI Revenue Recovery & Financial Safety Engine**

"RecoverAI autonomously identifies recoverable payment failures, evaluates economic value, lets AI advise but never control money, blocks unsafe actions deterministically, verifies recovery independently, learns from verified outcomes, and proves the resulting financial impact."

> **Core Principle:**  
> *AI recommends. Deterministic controls decide. Independent verification proves.*

---

## 1. Problem Statement

In online payment processing:
- **Payment failures cause massive revenue leakage**: 15–20% of `payment.failed` webhooks are transient false alarms (*Late-Authorization Flip-Flops*) where money arrives seconds or minutes later.
- **Naive systems blindly retry**: Automated retry bots attempt recovery on every failure, double-charging customers, causing expensive chargeback disputes, and destroying brand trust.
- **Hard declines are retried dangerously**: Attempting retries on hard declines (`CARD_BLOCKED`, `EXPIRED_CARD`, `INVALID_VPA`) triggers payment network penalty fines and gateway rate limiting.
- **Gateway success ≠ verified financial recovery**: A provider's HTTP 200 response or payment link dispatch does not mean funds have safely settled into the merchant's ledger.
- **Modern recovery requires economic optimization AND financial safety**: Systems must balance Expected Net Value ($\text{ENV} = P(\text{recovery}) \times \text{Amount} - \text{Costs}$) against strict conservation of funds.

---

## 2. RecoverAI Solution & Lifecycle

RecoverAI operates an end-to-end 9-stage closed recovery loop:

$$\text{OBSERVE} \longrightarrow \text{REASON} \longrightarrow \text{PLAN} \longrightarrow \text{POLICY CHECK} \longrightarrow \text{FIREWALL} \longrightarrow \text{ACT} \longrightarrow \text{VERIFY} \longrightarrow \text{REPLAN / STOP}$$

- **Deterministic Financial Authority**: The language model and ML components operate as **advisory agents only**. They have **zero** authority over ledger state, expected net value calculations, firewall rules, or financial execution.
- **Ledger Supremacy**: Revenue is recognized as recovered **only** after independent state engine verification confirms ledger settlement.

---

## 3. Architecture & Core Subsystems

RecoverAI is structured into modular, decoupled packages in `src/`:

```
src/
├── ingestion/          # Webhook ingestion & raw event normalization (processor.py)
├── state_engine/       # Deterministic Financial State Engine (engine.py, models.py)
├── intelligence/       # ML opportunity scoring, candidate generation & economic ranking
├── agent/              # Advisory LLM agent, policy engine & recovery firewall (firewall.py)
├── execution/          # Idempotent gateway executor & independent verifier (verifier.py)
├── learning/           # Verified outcome store, calibration & drift detection (drift.py)
├── challenger/         # Offline champion/challenger evaluation & promotion governance
├── replay/             # Replay engine & evidence graph provenance builder (graph.py)
├── observability/      # 17-operation telemetry, decision tracing & health checking
├── proof/              # Secret-redacted configuration hasher & final financial proof engine
├── api/                # FastAPI server, auth/RBAC dependencies & control plane routes
├── gateway/            # Sandbox mock gateway & Razorpay Test Mode integration adapter
└── chaos/              # Extended 16-scenario failure injection & chaos runner
```

---

## 4. Intelligent Recovery Engine (Step 18)

Located in `src/intelligence/`:
- **Deterministic Failure Classification** (`failure_classifier.py`): Categorizes events into `SOFT_TRANSIENT`, `HARD_DECLINE`, `ALREADY_RECOVERED`, `UNCERTAIN`, or `EXCEPTION`.
- **Recovery Opportunity Scoring** (`src/recovery/model.py`): Calibrated XGBoost ML model predicting $P(\text{recovery} \mid \text{context})$.
- **Candidate Action Generation** (`candidate_generator.py`): Generates candidate actions (`RETRY`, `PAYMENT_LINK`, `REMINDER`, `ESCALATE`, `STOP`).
- **Economic Ranking** (`economic_ranker.py`): Ranks candidates by transparent Expected Net Value ($\text{ENV} = P \times \text{Amount} - \text{Costs}$).
- **Advisory LLM Agent** (`src/intelligence/agent.py`): Queries the LLM for advisory planning within prompt-injection isolated bounds (`MAX_AGENT_STEPS = 3`).
- **Deterministic Override**: If the LLM recommendation is mathematically inferior ($\Delta \text{ENV} < 0$) or unsafe, the system deterministically overrides it with the top-ranked safe action.

---

## 5. Learning, Outcome Calibration & Governance (Step 19)

Located in `src/learning/` and `src/challenger/`:
- **Verified Outcome Learning**: Records expected vs actual recovery outcomes into an append-only outcome store (`OutcomeStore`).
- **Calibration & Drift Detection**: Monitors TVD (Total Variation Distance) failure distribution drift (threshold 0.15) and success rate delta (threshold 0.05).
- **Champion/Challenger Engine**: Evaluates candidate strategies offline over identical synthetic populations.
- **Human Approval & ADMIN Promotion**: 
  > **RecoverAI does NOT automatically promote a challenger.**  
  > Promotions require explicit `ADMIN` role authentication via `POST /api/control/challenger/promote`.
- **Cryptographic Versioning**: Tracks strategy lifecycle (`PROPOSED` $\to$ `EVALUATING` $\to$ `APPROVAL_REQUIRED` $\to$ `APPROVED` $\to$ `PROMOTED`) with rollback capabilities.

---

## 6. Production Readiness & Observability (Step 20)

Located in `src/observability/` and `src/proof/`:
- **17 Telemetry Operation Envelopes**: Structured events with global `correlation_id` tracking every lifecycle step.
- **15-Stage Decision Trace**: Reconstructs end-to-end decision graphs per payment without side-effects (`DecisionTracer`).
- **p50/p95/p99 Latency Tracking**: Real-time percentiles via thread-safe `LatencyRecorder`. Reports `INSUFFICIENT_DATA` when samples < 5.
- **Health & Dependency Classification**:
  - `CRITICAL` (Financial State Engine, Policy Engine, Firewall, Verification): Failures block execution and trigger `APPLICATION_UNHEALTHY`.
  - `NON_CRITICAL` (LLM, Learning, Drift, Metrics): Failures degrade system to `APPLICATION_DEGRADED` while recovery continues safely on the active champion.
- **Cryptographic Financial Proof**: `FinalProofEngine` produces `FINAL_PROOF_SHA256` binding population hashes, secret-redacted configuration hashes, and accounting invariants.

---

## 7. Financial Safety Invariants

Validated properties across all tested scenarios and lifecycles:

| Safety Invariant | Guaranteed Value | Description |
|---|:---:|---|
| **Phantom Revenue** | **₹0** | No unverified gateway status is claimed as recovered revenue. |
| **Duplicate Recovery** | **0** | Idempotency and session history block double-charging. |
| **Accounting Imbalance** | **₹0.00** | $\text{Processed} = \text{Recovered} + \text{Withheld} + \text{Pending} + \text{Escalated}$. |
| **Unsafe Actions Executed** | **0** | Retries on hard declines (`CARD_BLOCKED`) are 100% blocked by the firewall. |
| **Unverified Recovery** | **0** | Every recovery claim requires independent ledger confirmation. |
| **Unauthorized Execution** | **0** | Requests without valid authentication keys are rejected (401/403). |
| **Unauthorized Promotion** | **0** | Non-ADMIN users cannot promote challenger strategies. |
| **Automatic Policy Changes** | **0** | Policies remain immutable unless updated by authorized humans. |
| **Automatic Champion Promotions** | **0** | Offline learning cannot auto-promote without human ADMIN sign-off. |

---

## 8. Economic Evaluation (Step 20 Benchmark)

Evaluated over **10,000 synthetic payment lifecycles** (Seed: 42):

| Strategy | Total Net Value (₹) | Safety Violations | Performance Lift |
|---|:---:|:---:|:---:|
| **Naive Baseline** | ₹12,352,868.20 | 0 (after filtering) | Baseline |
| **Deterministic RecoverAI** | ₹14,756,170.00 | 0 | **+19.5% (+₹2,403,301.80)** |
| **Intelligent RecoverAI** | ₹14,756,170.00 | 0 | **+19.5% (+₹2,403,301.80)** |
| **Champion Strategy** | ₹14,756,170.00 | 0 | **+19.5% (+₹2,403,301.80)** |

> *Note:* The Step 20 10,000-scenario benchmark showed the deterministic, intelligent, and champion strategies converging to the same net value. RecoverAI's advantage in this benchmark comes from its controlled recovery strategy and safety architecture; the system does not artificially claim additional AI lift when the measured result is equal.

---

## 9. Decision Replay & Evidence Graph

Located in `src/replay/`:
- **Simulation-Only Replay**: Reconstructs candidate action evaluations and decision trees without invoking live gateways.
- **Evidence Nodes & Edges**: Builds directed acyclic provenance graphs detailing why an action was selected or blocked.
- **Tamper Detection**: SHA-256 cryptographic hashing guarantees replay integrity and detects any historical tampering.

---

## 10. Security & Access Control (RBAC)

- **Authentication**: API key validation (`X-API-Key` header) using constant-time string comparison (`secrets.compare_digest`).
- **Role-Based Access Control (RBAC)**:
  - `VIEWER`: Read-only dashboard access.
  - `AUDITOR`: Access to decision traces, replay, and audit logs.
  - `OPERATOR`: Ability to trigger simulations and run challenger evaluations.
  - `ADMIN`: Full authority including approving and promoting challenger strategies.
- **Security Hardening**: CORS policies, rate limiting, security headers, automatic sensitive data redaction (`AuditLogger`), and strict live-transaction hard-blocking (`RECOVERAI_LIVE_TRANSACTIONS=false`).

---

## 11. Payment Gateway Integration (Razorpay Test Mode)

Located in `src/gateway/`:
- **Sandbox Adapter**: Provider-agnostic `PaymentGateway` interface with `MockPaymentGateway` and `RazorpayGatewayAdapter`.
- **Razorpay Test Mode**: Supports checkout order creation, status checks, and webhook ingestion (`payment.failed`, `payment.authorized`, `payment.captured`).
- **HMAC-SHA256 Webhook Verification**: Verifies raw webhook signatures using merchant secret.
- **Event Idempotency**: Prevents duplicate webhook re-injection from distorting accounting metrics.
- **Live Transaction Hard-Block**: Real money execution is explicitly disabled unless securely configured in production.

---

## 12. Reliability & Chaos Failure Injection

Validated by `Step20ChaosRunner` (`src/chaos/scenarios_step20.py`):
- **16 Failure Injection Scenarios**: Covers LLM timeouts, malformed JSON, gateway 500/401 errors, verifier outages, unauthorized promotions, configuration tampering, and concurrent execution (10/50/100 threads).
- **Chaos Suite Result**: **16/16 PASSED** with 0 phantom revenue, 0 duplicate recoveries, and 0 accounting imbalances.

---

## 13. Verified Test & Build Status

- **Pytest Regression Suite**: **299 Passed, 8 Skipped, 0 Failed** (307 collected tests)
- **Frontend Production Build**: **PASS** (`vite build` completed in 11.04s, 1956 modules transformed)

---

## 14. Running the System & Demonstrations

### Prerequisites
- Python 3.10+
- Node.js 18+

### Setup Environment
```powershell
$env:AI_MODE="demo"
$env:PYTHONPATH="src"
```

### Run Full Master System Demo
Executes all 20 steps of closed-loop recovery, benchmarks, chaos tests, and final financial proof:
```powershell
python demo_full_system.py
```

### Run Automated Test Suite
```powershell
pytest -q
```

### Run Frontend Development Server
```powershell
cd frontend
npm install
npm run dev
```

---

## 15. Official Demo Video

- **Path**: `demo/RecoverAI_Final_Demo.mp4`
- **Duration**: ~5:00 minutes
- **Format**: 1920x1080 MP4 (H.264 / AAC)

---

## 16. Technical & Operational Limitations

1. **Simulation Default**: RecoverAI defaults to simulation and Razorpay Test Mode; live money execution requires explicit, secure production configuration.
2. **Offline Challenger Governance**: Machine learning models and challenger strategies cannot auto-promote; human ADMIN sign-off is required.
3. **Synthetic Economic Benchmarks**: Benchmark evaluations utilize synthetic payment populations calibrated to realistic fintech distributions.
4. **Production Deployment Requirements**: Real-world deployment requires dedicated database persistence, key vaults, SSL termination, and production gateway credentials.

---

## 17. Final Project Statement

> **"RecoverAI is not an AI that blindly retries payments.**  
> **It is an agentic financial recovery system where AI proposes, deterministic controls decide, execution is guarded, and independent verification proves whether money was actually recovered."**
