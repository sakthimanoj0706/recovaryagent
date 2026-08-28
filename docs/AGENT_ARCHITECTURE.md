# RecoverAI — Agentic Recovery Architecture

> **"Prove the money. Prioritize the chase. Recover it."**  
> Core Slogan: **PROVE → PRIORITIZE → PLAN → GUARD → ACT → VERIFY**

---

## 1. Executive Summary & Core Principle

In financial systems, a failed payment event (`payment.failed`) does **NOT** automatically mean money is lost. Furthermore, an AI agent's claim that a payment was recovered does **NOT** mean money is in the merchant's bank account.

RecoverAI implements a bounded agentic architecture where the Large Language Model (LLM) acts strictly as an **ADVISORY PLANNER**. The AI has **ZERO AUTHORITY** over financial truth, unit economics, deterministic safety gates, or recovery verification.

---

## 2. Bounded Architecture Pipeline

```
                     RAW PAYMENT & EVENT STREAM
                                 ↓
                  [STAGE 1: PROVE (Financial State Engine)]
                                 ↓
                      ONLY 'VERIFIED_LOST'?
                     /                     \
             (YES)  /                       \ (NO)
                   ↓                         ↓
    [STAGE 2: PRIORITIZE (Economics & ML)]   HALT (ALREADY_RECOVERED / UNCERTAIN / EXCEPTION)
                   ↓
         EXPECTED NET VALUE > ₹0?
        /                        \
(YES)  /                          \ (NO)
      ↓                            ↓
[STAGE 3: PLAN (Agentic Planner)]   CORRECTLY_WITHHELD (Negative ENV)
(Gemini / OpenRouter)
      ↓ (Structured AgentRecommendation)
[STAGE 4: GUARD (Deterministic Firewall)]
  • Prohibited Action Checks
  • Hard Decline Veto (CARD_BLOCKED)
  • Retry Limit Cap (Max 3 retries)
  • Idempotency Gate
      ↓
[STAGE 5: ACT (Action Executor)]
(Simulated Dispatch: PAYMENT_LINK / RETRY / REMINDER)
      ↓
[STAGE 6: VERIFY (Financial State Engine)]
(Independent Ledger Re-check: "NEVER TRUST THE AGENT")
      ↓
[IMMUTABLE AUDIT TRAIL & SYSTEM METRICS]
```

---

## 3. Clear Boundaries: What AI Does vs. What AI Does NOT Do

| Dimension | WHAT THE AI DOES ✅ | WHAT THE AI DOES NOT DO ❌ |
| :--- | :--- | :--- |
| **Financial State** | Receives immutable `VERIFIED_LOST` context. | Cannot classify or modify financial state. |
| **Unit Economics** | Considers Expected Net Value when choosing channel. | Cannot calculate or alter Expected Net Value or Probability. |
| **Intervention Strategy** | Recommends the safest action (`PAYMENT_LINK`, `REMINDER`, etc.). | Cannot invent unsupported payment actions. |
| **Communication** | Selects channel (`whatsapp`, `sms`) and tone. | Cannot send unapproved messages or spam customers. |
| **Safety Compliance** | Proposes action conforming to policy hints. | Cannot bypass deterministic Firewall rules (e.g. hard decline blocks). |
| **Verification & Truth** | Submits action for execution. | Cannot declare a payment recovered; verification belongs to State Engine. |

---

## 4. The 14 Non-Negotiable Safety Rules

1. `ALREADY_RECOVERED` must never reach the agent.
2. `UNCERTAIN` must never reach the agent.
3. `EXCEPTION` must never reach the agent.
4. Negative Expected Net Value ($ENV \le ₹0$) must never reach the agent.
5. Hard-decline retry (`CARD_BLOCKED`, `INVALID_ACCOUNT`, etc.) must never be approved.
6. The LLM cannot modify `financial_state`.
7. The LLM cannot modify `recovery_probability`.
8. The LLM cannot modify `expected_net_value`.
9. The LLM cannot bypass firewall rules.
10. The LLM cannot declare a payment recovered.
11. Only the deterministic Financial State Engine can determine recovery.
12. Every agent recommendation must be validated against the structured `AgentRecommendation` schema before reaching the firewall.
13. Every agent decision and firewall outcome must be written to the append-only audit log.
14. The maximum retry count remains strictly 3.

---

## 5. Structured Data Contracts

### A. Immutable Context (`RecoveryContext`)
```python
class RecoveryContext(BaseModel):
    payment_id: str
    order_id: Optional[str]
    amount: float
    financial_state: str           # Must be 'VERIFIED_LOST'
    failure_code: Optional[str]
    failure_description: Optional[str]
    hardness: Optional[str]        # 'soft' or 'hard'
    customer_segment: Optional[str]
    recovery_probability: Optional[float]
    expected_net_value: Optional[float]
    retry_count: int
    allowed_actions: List[str]
```

### B. Structured Recommendation (`AgentRecommendation`)
```python
class AgentRecommendation(BaseModel):
    action: RecoveryAction         # RETRY | PAYMENT_LINK | REMINDER | ESCALATE | STOP
    channel: Optional[str]         # whatsapp | sms | email | gateway
    timing: Optional[str]          # immediate | delayed_15m | backoff_exponential
    message_strategy: Optional[str]
    rationale: str
    confidence: float              # Clamped [0.0, 1.0]
    policy_references: List[str]
    observed_failure: Optional[str]
    selected_strategy: Optional[str]
    policy_basis: Optional[str]
    risk_level: Optional[str]
```

---

## 6. Two Hero Metrics

1. 🏆 **₹ ACTUALLY RECOVERED**: Confirmed captured by Financial State Engine post-intervention.
2. 🛡️ **₹ CORRECTLY WITHHELD**: Intentionally blocked from recovery pursuit (due to late authorization, uncertain state, negative unit economics, or hard decline).

---

## 7. 5-Minute Hiring Pitch

> "Most payment recovery systems do one of two things: they naively retry failed webhooks causing double charges and angry customers, or they give an LLM unchecked access to API tools.
> 
> **RecoverAI solves this with bounded agentic architecture.**
> 
> First, our deterministic Financial State Engine proves whether money is genuinely lost, eliminating false chases like late authorizations (*'FAILED ≠ LOST'*). Second, our ML model ensures recovery is economically worthwhile. Third, an LLM advisor chooses the optimal customer intervention. Fourth, a deterministic safety firewall enforces hard decline and retry limits. Finally, when an action executes, we **never trust the agent's claim of success**—the Financial State Engine independently re-evaluates the ledger before a single rupee is marked recovered.
> 
> The result: **PROVE → PRIORITIZE → PLAN → GUARD → ACT → VERIFY**."
