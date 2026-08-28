# RecoverAI — Final System Architecture & Technical Specification

## 1. Problem Statement & Fintech Reality

In modern electronic commerce and real-time payment networks (e.g. UPI, IMPS, Cards, Netbanking):
- **15–20% of initial `payment.failed` webhooks are false alarms** where bank settlement succeeds asynchronously seconds later (*Late Authorization Flip-Flop*).
- **Blind retry loops double-charge customers**, triggering chargeback disputes and merchant trust destruction.
- **Retrying hard declines** (`CARD_BLOCKED`, `STOLEN_CARD`, `INVALID_ACCOUNT`) incurs network penalty fees and gateway throttling.
- **Negative Expected Value ($-\text{ENV}$) recoveries** cost more in payment links and SMS charges than the recovery value.

---

## 2. Solution: The Closed-Loop Bounded Agent

RecoverAI establishes an unshakeable boundary between probabilistic AI reasoning and deterministic financial truth:

> **"RecoverAI is not an LLM that controls payments. It is a bounded financial agent operating inside deterministic financial safety rails."**

---

## 3. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph INGESTION ["1. Event Ingestion Pipeline"]
        W[Gateway Webhook] --> VP[Webhook Parser]
        VP --> EN[Event Normalizer]
        EN --> EP[Idempotent Event Processor]
    end

    subgraph ENGINE ["2. Financial State Engine (PROVE)"]
        EP --> FSE[Deterministic State Machine]
        FSE -->|State Evaluation| FS{Financial State}
    end

    FS -->|ALREADY_RECOVERED| WITHHOLD[STOP & Withhold ₹]
    FS -->|UNCERTAIN| WAIT[WAIT for In-Flight Window]
    FS -->|EXCEPTION| ESC[ESCALATE to Operations]
    FS -->|VERIFIED_LOST| RECOV[Continue to Intelligence]

    subgraph INTELLIGENCE ["3. Recovery Intelligence (PRIORITIZE)"]
        RECOV --> ML[XGBoost Probability Model]
        ML --> ECON[Expected Net Value Calculator]
    end

    ECON -->|ENV <= 0| NEG[STOP: FIREWALL-002]
    ECON -->|ENV > 0| AGENT[4. Agentic Recovery Planner (PLAN)]

    subgraph AGENT_LOOP ["4. Bounded Advisory Agent"]
        AGENT --> POLICY[5. Strict Policy Engine]
        POLICY --> FW[6. Recovery Firewall (GUARD)]
    end

    subgraph EXECUTION ["5. Gateway & Verifier (ACT & VERIFY)"]
        FW -->|APPROVED| GW[Payment Gateway Sandbox]
        GW --> POST_EVT[Post-Action Webhooks]
        POST_EVT --> VER[7. Independent Closed-Loop Verifier]
        VER -->|Ledger Query| FSE
    end

    subgraph AUDIT ["6. Ledger & Observability"]
        VER --> AUDIT_LOG[Append-Only JSONL Audit Ledger]
        AUDIT_LOG --> UI[Command Center Dashboard]
    end
```

---

## 4. Subsystem Specifications

### 4.1 Financial State Engine (`src/state_engine/`)
- **Role:** Sole source of truth for payment states (`VERIFIED_LOST`, `ALREADY_RECOVERED`, `UNCERTAIN`, `EXCEPTION`).
- **Invariants:**
  - `payment.authorized` (late auth) or `payment.captured` $\longrightarrow$ `ALREADY_RECOVERED`.
  - In-flight transactions within clearing window $\longrightarrow$ `UNCERTAIN`.
  - Amount mismatch or refund without capture $\longrightarrow$ `EXCEPTION`.

### 4.2 Recovery Intelligence & Economics (`src/recovery/`)
- **Role:** Evaluates $P(\text{recovery})$ and Expected Net Value.
- **Formula:**
  $$\text{ENV} = \left( P(\text{recovery}) \times \text{Amount} \times (1 - \text{MDR}) \right) - \text{Retry Cost} - \text{Intervention Cost} - \text{Friction}$$

### 4.3 Agentic Recovery Planner (`src/agent/`)
- **Role:** Suggests optimal recovery channel (`PAYMENT_LINK`, `RETRY`, `REMINDER`, `ESCALATE`, `STOP`).
- **Constraint:** Strictly advisory. Cannot execute payments, change financial states, or override rules.

### 4.4 Policy Engine (`src/agent/policy.py`)
- **Role:** Filters unsupported actions and ensures adherence to merchant SLA action spaces.

### 4.5 Recovery Firewall (`src/agent/firewall.py`)
- **Role:** Non-bypassable deterministic safety gates:
  - `FIREWALL-002`: Negative ENV $\to$ STOP
  - `FIREWALL-004`: Hard Decline $\to$ STOP
  - `FIREWALL-005`: Max 3 Retries $\to$ STOP
  - `FIREWALL-006`: Already Recovered $\to$ STOP
  - `FIREWALL-007`: Uncertain State $\to$ WAIT
  - `FIREWALL-008`: Exception State $\to$ ESCALATE
  - `FIREWALL-009`: Duplicate Action $\to$ STOP

### 4.6 Payment Gateway Adapter (`src/gateway/`)
- **Role:** Provider-independent sandbox interface (`MockPaymentGateway`, `RazorpayGatewayAdapter`).
- **Constraint:** Strictly isolated in `SIMULATION MODE`.

### 4.7 Closed-Loop Verifier (`src/execution/verifier.py`)
- **Role:** Independently inspects post-action state engine records to verify genuine recovery.

### 4.8 Structured Audit Trail (`src/audit/`)
- **Role:** Append-only JSONL logging with persistent `run_id` correlation and verifiable accounting balance:
  $$\text{processed\_amount} = \text{amount\_recovered} + \text{amount\_withheld} + \text{amount\_pending} + \text{amount\_escalated}$$

---

## 5. Security & Idempotency Guarantees

| Boundary | Protection Mechanism | Invariant |
| :--- | :--- | :--- |
| **Webhook Ingestion** | `(provider, event_id)` store | Duplicate webhooks safely ignored |
| **Gateway Dispatch** | `(payment_id, action)` tracker | Zero double execution |
| **Retry Limits** | `FIREWALL-005` ($N \ge 3$) | Prohibits customer retry spam |
| **Late Auth** | `FIREWALL-006` | Intercepts flip-flops, preventing double charges |
| **Verification** | State Engine ledger query | Zero false recovery reporting |

---

## 6. Simulation Mode & Limitations

- **Simulation Mode:** All executions dispatch to mock/sandbox environments. No real bank accounts or funds are touched.
- **Production Integration Path:** Direct drop-in adapter replacement via Razorpay Webhook Ingestion (`POST /api/webhooks/payment`) and Razorpay SDK Dispatch.
