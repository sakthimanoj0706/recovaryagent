# STEP 17: PRODUCTION SECURITY HARDENING

## Threat Model
The system protects a critical financial ledger and decision engine from:
1. Unauthorized execution of financial workflows.
2. Webhook payload tampering or replays.
3. Live money accidental execution (hard-blocked by `RECOVERAI_LIVE_TRANSACTIONS`).
4. Sensitive data leakage (keys, secrets, full traces).

## Authentication
- **Protected Endpoints:** All API endpoints are protected using an `X-API-Key` header.
- **Unauthorized Requests Blocked:** Requests missing the API key or providing an invalid one receive an HTTP 401 response (except webhooks, which use HMAC).
- **Development Bypass:** For local UI development, if `RECOVERAI_ENV=development` and no API key is provided, a default `ADMIN` role is assumed.

## Authorization
- **RBAC:** Four roles implemented: `ADMIN`, `OPERATOR`, `AUDITOR`, `VIEWER`.
- **Privilege Escalation Blocked:** Enforced at the FastAPI route level via the `require_role()` dependency. 
    - `VIEWER` can read dashboards and recovery histories.
    - `OPERATOR` can execute recoveries.
    - `AUDITOR` can view immutable replay/evidence graphs.
    - `ADMIN` can trigger demo resets and provider tests.

## Secret Management
- **Hardcoded Secrets:** None. All API keys and webhook secrets are sourced exclusively from environment variables.
- **Constant-time Comparison:** Used `secrets.compare_digest` for API keys and HMAC webhook comparisons to defeat timing attacks.
- **Logs Redacted:** Integrated `_redact()` into the `AuditLogger` to strip fields containing terms like "secret", "password", "token", or "authorization".
- **Frontend Exposure:** Secrets are never sent in API responses (e.g. `get_provider_status` explicitly strips keys).

## Webhook Security
- **Invalid Signatures Blocked:** HMAC-SHA256 signatures validated against `RAZORPAY_WEBHOOK_SECRET`.
- **Modified Payload Blocked:** Alterations invalidate the HMAC signature.
- **Replay Blocked:** Deduplication enforced by `FinancialStateEngine` and duplicate events return a 409 or resolve to `ALREADY_RECOVERED`.
- **Duplicate Blocked:** Idempotency tracking across payment states.

## API Validation
- **Malformed Input Blocked:** Standard Pydantic rigid type checking.
- **Invalid Amounts Blocked:** Financial inputs (like `amount`) strictly enforce positive boundaries (e.g. `gt=0.0`).
- **Oversized Input Blocked:** `max_length` properties added to strings (e.g. `payment_id: str = Field(..., max_length=255)`).

## Rate Limiting
- **Protected Endpoints:** Implemented in-memory token bucket rate limiters (extensible to Redis).
- **Abuse Test:** High-capacity (`webhook_limiter`) for webhooks, restricted (`expensive_limiter`) for LLM/agent actions. Returns HTTP 429 when exhausted.

## Error Handling
- Stack traces are suppressed from API responses.
- Default `HTTPException` returns generic detail strings devoid of internal path or variable leaks.

## Audit Security
- **Integrity:** The `AuditLogger` remains append-only.
- **Sensitive Data Redaction:** Raw JSON payloads passed into the logger are deeply inspected to sanitize strings matching known credential formats before being written.

## Live-Mode Protection
- **Live Transactions Blocked:** Re-verified `assert_live_execution_disabled` and `LiveModeDisabledError`. Test and simulation modes explicitly partition execution logic.

## Dependency Security
- **Findings:** `npm audit` returned an issue for `esbuild` affecting the development server (`vite`).
- **Impact:** Does not affect RecoverAI since the app builds static assets for production execution. Upgrading would entail a major breaking change to Vite 8. Not recommended at this stage. Python core dependencies are secure.

## Security Test Results
- Pytest suite successfully tested: unauthenticated rejections, insufficient roles (VIEWER blocked from POST), missing fields, and rate-limiter boundaries.
- Total Green CI/CD: 242 Tests.
