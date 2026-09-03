"""
Step 20 — Configuration Integrity Hasher.

Produces a deterministic SHA-256 hash of RecoverAI's configuration.
NEVER includes secrets, API keys, or credentials in the hash input.
Same config → same hash. Different config → different hash.
"""

import hashlib
import json
import os
from typing import Dict, Any, Optional


# ── Fields that MUST NEVER be included in the configuration hash ──────────────
_SECRET_FIELDS = {
    "razorpay_key_secret", "razorpay_key_id", "razorpay_webhook_secret",
    "openrouter_api_key", "gemini_api_key", "recoverai_admin_key",
    "recoverai_operator_key", "recoverai_auditor_key", "recoverai_viewer_key",
    "api_key", "secret", "password", "token", "private_key",
}


def _redact_secrets(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively remove secret fields from a dict before hashing."""
    out = {}
    for k, v in d.items():
        if any(s in k.lower() for s in _SECRET_FIELDS):
            continue  # Omit entirely from hash input
        if isinstance(v, dict):
            out[k] = _redact_secrets(v)
        else:
            out[k] = v
    return out


class ConfigurationHasher:
    """
    Deterministic configuration hasher for RecoverAI.

    Collects: strategy, version, policy config, economic config, retry limits,
    risk parameters, feature flags, environment, provider mode.
    Excludes all secrets.
    """

    def snapshot(self) -> Dict[str, Any]:
        """Collect the current configuration snapshot (no secrets)."""
        config = {
            "strategy": {
                "id": "deterministic_v1",
                "version": "1.0",
                "max_agent_steps": 3,
                "llm_role": "ADVISORY_ONLY",
                "ml_role": "SCORING_ONLY",
                "financial_authority": "DETERMINISTIC_ENGINES_ONLY",
            },
            "policy": {
                "max_retry_count": 3,
                "hard_decline_codes": [
                    "CARD_BLOCKED", "CARD_EXPIRED", "BAD_VPA",
                    "INVALID_ACCOUNT", "EXPIRED_CARD"
                ],
                "idempotency_enforcement": True,
                "duplicate_action_blocked": True,
            },
            "economics": {
                "gateway_attempt_cost": 0.50,
                "payment_link_cost": 1.50,
                "customer_contact_cost": 0.25,
                "manual_escalation_cost": 50.00,
                "hard_decline_penalty_cost": 15.00,
                "double_recovery_chargeback_cost": 250.00,
                "minimum_net_value_threshold": 0.0,
            },
            "safety": {
                "live_transaction_hard_block": True,
                "phantom_revenue_tolerance": 0.0,
                "duplicate_recovery_tolerance": 0,
                "accounting_imbalance_tolerance": 0.0,
                "unsafe_executions_tolerance": 0,
                "automatic_promotion_allowed": False,
                "automatic_policy_change_allowed": False,
            },
            "rbac": {
                "promotion_requires_role": "ADMIN",
                "rollback_requires_role": "ADMIN",
                "audit_requires_role": "AUDITOR",
                "viewer_can_promote": False,
                "operator_can_promote": False,
            },
            "environment": {
                "env": os.getenv("RECOVERAI_ENV", "production"),
                "provider_mode": os.getenv("RECOVERAI_GATEWAY_PROVIDER", "SIMULATION"),
                "live_transactions": os.getenv("RECOVERAI_LIVE_TRANSACTIONS", "false").lower(),
                "ai_mode": os.getenv("AI_MODE", "demo").lower(),
            },
            "learning": {
                "learning_is_advisory": True,
                "learning_has_financial_authority": False,
                "drift_threshold_tvd": 0.15,
                "drift_threshold_success_rate": 0.05,
                "challenger_requires_human_approval": True,
            },
        }
        # Extra safety: redact any accidental secrets
        return _redact_secrets(config)

    def compute_hash(self, config: Optional[Dict[str, Any]] = None) -> str:
        """
        Compute CONFIGURATION_SHA256 from the given (or current) config snapshot.
        Deterministic: same config → same hash.
        """
        cfg = config if config is not None else self.snapshot()
        # Sort keys for determinism
        serialized = json.dumps(cfg, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def verify_determinism(self) -> bool:
        """Verify that two independent snapshots produce the same hash."""
        h1 = self.compute_hash()
        h2 = self.compute_hash()
        return h1 == h2

    def verify_sensitivity(self) -> bool:
        """Verify that a changed config produces a different hash."""
        original = self.snapshot()
        original_hash = self.compute_hash(original)

        # Mutate one field
        mutated = json.loads(json.dumps(original))  # deep copy
        mutated["strategy"]["max_agent_steps"] = 999
        mutated_hash = self.compute_hash(mutated)

        return original_hash != mutated_hash
