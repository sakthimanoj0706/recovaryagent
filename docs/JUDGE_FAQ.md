# RecoverAI — Judge & Fintech Executive FAQ

### Q1. Why not simply retry every failed payment?
**Answer:** In Indian and global payment ecosystems, retrying every failure causes three severe problems:
1. **Double-Charging:** 15–20% of soft failures (e.g. UPI timeouts) actually authorize asynchronously seconds later. Blind retries double-charge the customer.
2. **Bank Penalties & Network Blocks:** Retrying hard declines (e.g., `CARD_BLOCKED`, `STOLEN_CARD`, `INVALID_ACCOUNT`) incurs gateway penalty fees and risks card network sanctions.
3. **Negative Unit Economics:** Sending retries or payment links on small-ticket, low-intent checkouts costs more in gateway/SMS fees than the expected recovery value.

---

### Q2. What does "FAILED ≠ LOST" mean?
**Answer:** A `payment.failed` event from a payment gateway indicates a failure of the initial synchronous request, **not** that the merchant has permanently lost the money. In high-volume networks like UPI and Netbanking, late authorization flip-flops occur when bank settlements arrive asynchronously at $T+30\text{s}$ to $T+120\text{s}$. RecoverAI's Financial State Engine tracks event history over time to establish financial truth before any recovery action is initiated.

---

### Q3. Why do you need both Machine Learning and a deterministic Firewall?
**Answer:** 
- **Machine Learning (Recovery Intelligence)** answers: *"Is recovery economically worthwhile?"* (Predicts $P(\text{recovery})$ and calculates Expected Net Value).
- **Deterministic Firewall** answers: *"Is recovery safe and legally permitted?"* (Enforces hard non-bypassable constraints such as maximum 3 retries, no hard decline retries, and no action if already recovered).

---

### Q4. Can Gemini or an LLM override the Firewall?
**Answer:** **Never.** The LLM acts purely in an advisory capacity. In our architecture:
$$\text{LLM Recommendation} \longrightarrow \text{Strict Policy Filter} \longrightarrow \text{Deterministic Firewall Gate} \longrightarrow \text{Action}$$
If the LLM recommends `RETRY` on a hard decline or duplicate action, the Firewall immediately intercepts the request with `FIREWALL-004` or `FIREWALL-009`, halts execution, and logs the violation.

---

### Q5. What happens if the LLM hallucinates or generates invalid JSON?
**Answer:** The LLM's output is parsed through a strict Pydantic policy schema. If the response is unparseable, contains unsupported action strings, or the LLM service is completely unavailable, the orchestrator safely falls back to deterministic rule heuristics and operations escalation (`ESCALATE`), preventing any crash or unintended transaction.

---

### Q6. What if the gateway returns `SUCCESS` for an action, but the payment was not captured?
**Answer:** The Action Executor only records gateway delivery (e.g. payment link dispatched). The **Closed-Loop Verifier** independently queries the Financial State Engine ledger. If no subsequent `payment.captured` or `payment.authorized` event exists, the Verifier declares `RECOVERY_FAILED` and records ₹0.00 in the recovered bucket.

---

### Q7. What if a capture arrives 45 minutes after the failure?
**Answer:** The Ingestion Engine normalizes the late `payment.captured` webhook. The Financial State Engine transitions the payment from `VERIFIED_LOST` to `ALREADY_RECOVERED`. Any pending recovery actions or scheduled retries are immediately aborted by `FIREWALL-006`.

---

### Q8. What happens when a webhook arrives twice (Idempotency)?
**Answer:** The Ingestion Processor maintains an immutable `(provider, event_id)` store. Duplicate webhooks are intercepted as `DUPLICATE_EVENT` and safely acknowledged with zero state re-triggering and zero metric distortion.

---

### Q9. What happens after three retries?
**Answer:** `FIREWALL-005` strictly enforces the 3-attempt limit. If $N \ge 3$, the firewall emits `STOP` (`MAX_RETRY_PROTECTION`) and prohibits further automated retries to protect customer trust and avoid bank throttling.

---

### Q10. What happens with a settlement mismatch?
**Answer:** If the settled amount on the bank ledger differs from the order value (e.g., ₹8,000 settled for an ₹8,500 order), the Financial State Engine transitions the state to `EXCEPTION`. The orchestrator escalates the transaction directly to human operations (`ESCALATED_TO_OPERATIONS`) for manual reconciliation.

---

### Q11. Why is the Financial State Engine authoritative over the Agent?
**Answer:** Financial ledgers require mathematical determinism, commutativity, and strict compliance. An LLM is probabilistic and cannot be an auditor of financial truth. The Financial State Engine uses deterministic state machine rules to establish the single source of truth.

---

### Q12. Can this execute real payments?
**Answer:** No. RecoverAI is configured with a strict `SIMULATION_MODE = True` flag. All gateway actions dispatch through sandbox adapters or mock simulation harnesses. No real bank rails are touched.

---

### Q13. How would this integrate with Razorpay?
**Answer:** RecoverAI integrates via two standard touchpoints:
1. **Inbound:** Webhook endpoint (`POST /api/webhooks/payment`) receiving `payment.failed`, `payment.authorized`, `payment.captured`, and `order.paid` events.
2. **Outbound:** `RazorpayGatewayAdapter` using the official Razorpay SDK (`orders.create`, `payment_link.create`, `payments.capture`).

---

### Q14. How is Expected Net Value (ENV) calculated?
**Answer:**
$$\text{ENV} = \left( P(\text{recovery}) \times \text{Amount} \times (1 - \text{MDR}) \right) - \text{Retry Cost} - \text{Intervention Cost} - \text{Customer Friction}$$
If $\text{ENV} \le 0$, `FIREWALL-002` blocks recovery because the cost of recovery exceeds the expected return.

---

### Q15. What happens when the LLM/API is unavailable?
**Answer:** RecoverAI implements offline-first deterministic fallbacks. If OpenRouter or Gemini APIs timeout or throw 5xx errors, the orchestrator falls back to calibrated decision tree heuristics without dropping payments or blocking the pipeline.

---

### Q16. How do you prevent double charging?
**Answer:** Through the invariant check in `FIREWALL-006` (`ALREADY_RECOVERED` $\to$ `STOP`) and strict boundary idempotency across webhooks, gateway dispatches, and verification queries.

---

### Q17. How do you prevent false recovery reporting?
**Answer:** The system separates Action Status from Verification State. A payment is **only** booked into the `total_amount_recovered` metric when the independent Financial State Engine verifies confirmed settlement on the ledger.
