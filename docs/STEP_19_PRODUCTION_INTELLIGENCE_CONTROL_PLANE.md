# Step 19: Production Intelligence & Control Plane

## Architecture
The learning layer creates a comprehensive feedback loop without ever granting financial execution authority to the ML engine.
- **Outcome Learning (`src/learning`)**: Records deterministically traced lifecycle outcomes in the `OutcomeStore`.
- **Metrics & Calibration (`metrics.py`, `calibration.py`)**: Quantifies predicted probability vs reality and outputs a blended Decision Quality Score.
- **Drift Detection (`drift.py`)**: Uses Total Variation Distance (TVD) for failure distributions and absolute delta for success-rate drifts. Emits STABLE, WARNING, or DRIFT_DETECTED.
- **Champion / Challenger (`src/challenger`)**: Compares a proposed offline challenger strategy against the current champion by reusing the Step 15 Synthetic Simulation Engine over identical random seeds.

## Safety & Invariants
- **LLM/ML Advisory Limit**: ML and LLM models *cannot* bypass the Step 12 Firewall or Step 10 Financial State Engine.
- **Why RecoverAI does not automatically learn financial policy**:
    Learning proposes.
    Evaluation measures.
    Humans approve.
    Policy controls.
    Firewall enforces.
    Verification proves.
    Ledger decides financial truth.

## Governance & API
- **Endpoints**: `POST /api/control/outcomes/record`, `GET /api/control/calibration`, `GET /api/control/drift`, `POST /api/control/challenger/evaluate`, etc.
- **RBAC Enforcement**: `require_role(Role.ADMIN)` strictly gates `POST /api/control/challenger/promote`.
- **Frontend Control Plane**: A dashboard component (`RecoveryControlPlane.tsx`) visualizes offline evaluation vs champion and enables manual promotion for Admins.

## Limitations
- In-memory `OutcomeStore` does not persist across restarts; requires migration to a persistent store (Postgres/Redis).
- Evaluation engine relies heavily on synthetic data since live transactional A/B testing is considered too risky in this phase.
