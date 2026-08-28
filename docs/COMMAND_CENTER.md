# RecoverAI — Recovery Command Center

> **"Prove the money. Prioritize the chase. Recover it."**  
> Complete Architectural & Operational Guide for the RecoverAI Command Center.

---

## 1. Executive Summary & Design Vision

The RecoverAI Command Center is a high-density, production-grade fintech dashboard engineered to demonstrate the end-to-end bounded recovery closed loop:

$$\text{PROVE} \longrightarrow \text{PRIORITIZE} \longrightarrow \text{PLAN} \longrightarrow \text{GUARD} \longrightarrow \text{ACT} \longrightarrow \text{VERIFY}$$

Unlike traditional dashboards that display static charts or naively automate webhooks, the Command Center makes the **agentic financial decision process and safety guardrails visible in real time**.

---

## 2. Dashboard Architecture & Tech Stack

### Frontend Stack
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS (Dark fintech aesthetic, glassmorphism, high density)
- **Motion & Animations**: Framer Motion
- **Iconography**: Lucide React
- **Visual Charts**: Recharts

### Backend Stack
- **API Framework**: FastAPI + Uvicorn
- **Engines**:
  - `FinancialStateEngine` (Deterministic truth)
  - `RecoveryProbabilityModel` (Logistic Regression ML)
  - `Expected Net Value Calculator` (Configurable unit economics)
  - `AgenticRecoveryPlanner` (Advisory LLM)
  - `RecoveryFirewall` (10 deterministic safety rules)
  - `ActionExecutor` & `SyntheticSimulationEngine`
  - `RecoveryVerifier` (Independent ledger proof)
  - `AuditLogger` (Append-only JSONL trail)

---

## 3. Component Hierarchy

```
frontend/src/
├── App.tsx                        # Main Layout & Live Animation Orchestration
├── api.ts                         # Typed API client bridging to FastAPI
├── types.ts                       # Shared TypeScript interfaces
└── components/
    ├── Header.tsx                 # Brand, Status indicator, Audit modal trigger
    ├── HeroMetrics.tsx            # 6 Hero KPIs + Synthetic dataset banner
    ├── ScenarioSimulator.tsx      # 5 Quick Trigger buttons for live scenario execution
    ├── LivePipeline.tsx           # 6-Stage animated horizontal pipeline
    ├── FlipFlopHighlight.tsx      # 3 Core Showcase Tabs (Failed≠Lost, Economics, Verification)
    ├── WhyDidWeActPanel.tsx       # Decision matrix & reasoning explainability
    ├── VerificationProofPanel.tsx # Agent Claim vs Financial Truth comparison
    ├── AgentActivityStream.tsx    # Structured telemetry (No hidden chain-of-thought)
    ├── FirewallView.tsx           # Deterministic safety rules inspection
    ├── PaymentsExplorer.tsx       # Searchable & filterable payments ledger table
    ├── PaymentDetailPanel.tsx     # Slide-out truth audit & event history drawer
    └── AuditTrailModal.tsx        # Immutable audit trail explorer
```

---

## 4. Backend API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/metrics` | Returns aggregated metrics (₹ Recovered, ₹ Withheld, Safe Stops, etc.). |
| `GET` | `/api/payments` | Paginated, filterable list of payment records and financial states. |
| `GET` | `/api/payments/{id}` | Detailed payment evaluation, unit economics, and raw lifecycle events. |
| `POST` | `/api/recovery/{id}` | Runs full closed-loop recovery workflow on a specific payment. |
| `POST` | `/api/demo/{scenario}` | Triggers one of the 5 predefined hiring demo scenarios. |
| `GET` | `/api/audit` | Returns immutable audit trail records in reverse chronological order. |

---

## 5. The 5-Minute Razorpay Hiring Demo Flow

### Step 1: Open the Command Center (0:00 - 0:45)
- Point to the **Hero Metrics**:
  - 🏆 **₹10,000.00 Actually Recovered** (Confirmed captured post-action)
  - 🛡️ **₹37,500.00 Correctly Withheld** (Saved from unnecessary or unsafe chases)
- Emphasize the core thesis: *"In fintech, a failed webhook does NOT mean money is lost. RecoverAI proves the money before it chases."*

### Step 2: Showcase #1 — "FAILED ≠ LOST" Flip-Flop (0:45 - 2:00)
- Click **`🛡 Scenario 2 — Failed ≠ Lost`** on the Quick Bar or Showcase Tab.
- Observe the pipeline animation:
  1. `payment.failed` ingested.
  2. Financial State Engine proves a subsequent capture cleared 45 mins later $\to$ **`ALREADY_RECOVERED`**.
  3. LLM is **NOT CALLED**. Firewall halts pursuit (`FIREWALL-006`).
  4. **₹25,000.00 Correctly Withheld**.
- Takeaway: *"Traditional automated retries double-charge the customer. RecoverAI prevents double charges by proving state first."*

### Step 3: Showcase #2 — "ECONOMICS ≠ PERMISSION" (2:00 - 3:15)
- Click **`🚫 Scenario 3 — Hard Decline`**.
- Observe the pipeline:
  1. Amount is ₹12,000, $P = 14.27\%$, Expected Net Value is positive ($+₹1,632$).
  2. The LLM advisor sees high value and recommends `RETRY`.
  3. The deterministic Firewall steps in with **`FIREWALL-004` (STOP)**: *CARD_BLOCKED is a hard decline.*
  4. **₹12,000.00 Correctly Withheld**.
- Takeaway: *"An ML opportunity is never permission to violate payment network policy."*

### Step 4: Showcase #3 — "AGENT CLAIM ≠ FINANCIAL TRUTH" (3:15 - 4:15)
- Click **`🔍 Scenario 5 — Verification Catch`**.
- Observe the pipeline:
  1. Payment Link was dispatched (`SIMULATED_SUCCESS`).
  2. The verifier queries the Financial State Engine.
  3. State Engine confirms payment remains `VERIFIED_LOST` (customer did not complete checkout).
  4. Outcome is declared **`RECOVERY_FAILED`** (₹0 falsely recorded).
- Takeaway: *"We NEVER trust the agent or executor. Only the bank ledger proves recovery."*

### Step 5: Normal Recovery & Audit Trail (4:15 - 5:00)
- Click **`▶ Scenario 1 — Recover ₹10,000`**.
- Observe the clean success path: `VERIFIED_LOST` $\to$ Positive ENV $\to$ `PAYMENT_LINK` $\to$ `APPROVED` $\to$ `CAPTURED` $\to$ **₹10,000.00 RECOVERED**.
- Open the **Audit Trail** button in the header to demonstrate immutable, append-only traceability.

---

## 6. How to Launch

```bash
# 1. Start the FastAPI Backend (Port 8000)
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

# 2. Start the React Frontend (Port 5173)
cd frontend
npm run dev
```
Navigate to `http://localhost:5173` in your browser.
