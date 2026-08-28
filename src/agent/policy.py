"""
Deterministic Policy Registry and Policy Engine for RecoverAI.
Guarantees that the LLM cannot propose or execute actions that violate fintech safety policies.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from .models import RecoveryAction, RecoveryPriority, RecoveryContext, AgentRecommendation
from .schemas import AgentAction, PolicyCheckRecord


@dataclass
class FailurePolicy:
    failure_code: str
    allowed_actions: List[RecoveryAction]
    prohibited_actions: List[RecoveryAction]
    recommended_channel: str
    retry_eligibility: bool
    max_retry_count: int = 3
    description: str = ""


# Deterministic Failure Policy Registry
FAILURE_POLICY_REGISTRY: Dict[str, FailurePolicy] = {
    "INSUFFICIENT_FUNDS": FailurePolicy(
        failure_code="INSUFFICIENT_FUNDS",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="whatsapp",
        retry_eligibility=False,
        max_retry_count=0,
        description="Soft decline. Retrying with identical balance fails; direct payment link or gentle reminder is required.",
    ),
    "BANK_DOWNTIME": FailurePolicy(
        failure_code="BANK_DOWNTIME",
        allowed_actions=[RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.WAIT, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[],
        recommended_channel="gateway",
        retry_eligibility=True,
        max_retry_count=3,
        description="Transient bank failure. Safe to retry with exponential backoff or send alternative payment link.",
    ),
    "TIMEOUT": FailurePolicy(
        failure_code="TIMEOUT",
        allowed_actions=[RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[],
        recommended_channel="gateway",
        retry_eligibility=True,
        max_retry_count=3,
        description="Gateway timeout. Safe to retry after short backoff.",
    ),
    "NETWORK_ERROR": FailurePolicy(
        failure_code="NETWORK_ERROR",
        allowed_actions=[RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[],
        recommended_channel="gateway",
        retry_eligibility=True,
        max_retry_count=3,
        description="Transient network error. Safe to retry.",
    ),
    "GATEWAY_ERROR": FailurePolicy(
        failure_code="GATEWAY_ERROR",
        allowed_actions=[RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[],
        recommended_channel="gateway",
        retry_eligibility=True,
        max_retry_count=3,
        description="Gateway internal glitch. Eligible for automated retry.",
    ),
    "CARD_BLOCKED": FailurePolicy(
        failure_code="CARD_BLOCKED",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="email",
        retry_eligibility=False,
        max_retry_count=0,
        description="Hard decline. Card is permanently or administratively blocked. Automated RETRY is strictly prohibited.",
    ),
    "INVALID_ACCOUNT": FailurePolicy(
        failure_code="INVALID_ACCOUNT",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="email",
        retry_eligibility=False,
        max_retry_count=0,
        description="Hard decline. Account does not exist. Retrying is prohibited.",
    ),
    "EXPIRED_CARD": FailurePolicy(
        failure_code="EXPIRED_CARD",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="sms",
        retry_eligibility=False,
        max_retry_count=0,
        description="Hard decline. Card has expired. Must request updated payment instrument.",
    ),
    "CARD_EXPIRED": FailurePolicy(
        failure_code="CARD_EXPIRED",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="sms",
        retry_eligibility=False,
        max_retry_count=0,
        description="Hard decline. Card has expired. Must request updated payment instrument.",
    ),
    "BAD_VPA": FailurePolicy(
        failure_code="BAD_VPA",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.ESCALATE, RecoveryAction.STOP],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="sms",
        retry_eligibility=False,
        max_retry_count=0,
        description="Hard decline. UPI VPA address is invalid or deleted. Automated RETRY is strictly prohibited.",
    ),
    "USER_CANCELLED": FailurePolicy(
        failure_code="USER_CANCELLED",
        allowed_actions=[RecoveryAction.REMINDER, RecoveryAction.PAYMENT_LINK, RecoveryAction.STOP, RecoveryAction.ESCALATE],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="sms",
        retry_eligibility=False,
        max_retry_count=0,
        description="Customer intentionally cancelled flow. Do not force automated retry.",
    ),
    "INVALID_OTP": FailurePolicy(
        failure_code="INVALID_OTP",
        allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.STOP, RecoveryAction.ESCALATE],
        prohibited_actions=[RecoveryAction.RETRY],
        recommended_channel="whatsapp",
        retry_eligibility=False,
        max_retry_count=0,
        description="Authentication failed. Cannot retry without user initiating a new session.",
    ),
}

DEFAULT_SOFT_POLICY = FailurePolicy(
    failure_code="DEFAULT_SOFT",
    allowed_actions=[RecoveryAction.RETRY, RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER, RecoveryAction.ESCALATE, RecoveryAction.STOP],
    prohibited_actions=[],
    recommended_channel="gateway",
    retry_eligibility=True,
    max_retry_count=3,
    description="Generic soft failure. Permitted for safe retry or payment link.",
)

DEFAULT_HARD_POLICY = FailurePolicy(
    failure_code="DEFAULT_HARD",
    allowed_actions=[RecoveryAction.PAYMENT_LINK, RecoveryAction.ESCALATE, RecoveryAction.STOP],
    prohibited_actions=[RecoveryAction.RETRY],
    recommended_channel="email",
    retry_eligibility=False,
    max_retry_count=0,
    description="Generic hard failure. Retrying is prohibited.",
)


def get_failure_policy(failure_code: Optional[str], hardness: Optional[str] = None) -> FailurePolicy:
    """Retrieve the policy configuration for a given failure code."""
    if failure_code and failure_code.upper() in FAILURE_POLICY_REGISTRY:
        return FAILURE_POLICY_REGISTRY[failure_code.upper()]
    if hardness and hardness.lower() == "hard":
        return DEFAULT_HARD_POLICY
    return DEFAULT_SOFT_POLICY


class PolicyEngine:
    """
    Deterministic Policy Engine executing pre-Firewall validation checks.
    """

    def __init__(self):
        self.check_history: List[PolicyCheckRecord] = []

    def _record_check(self, policy_name: str, rule_id: str, passed: bool, reason: str) -> PolicyCheckRecord:
        rec = PolicyCheckRecord(
            policy_name=policy_name,
            rule_id=rule_id,
            passed=passed,
            reason=reason,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.check_history.append(rec)
        return rec

    def validate_action_space(self, action_str: str) -> Tuple[bool, Optional[str]]:
        """Validate that proposed action belongs to allowed action space."""
        if not AgentAction.is_valid_action(action_str):
            reason = f"Action '{action_str}' is not in allowed action space: {[a.value for a in AgentAction]}"
            self._record_check("ACTION_SPACE_VALIDATION", "POLICY-000", False, reason)
            return False, reason
        self._record_check("ACTION_SPACE_VALIDATION", "POLICY-000", True, f"Action '{action_str}' is valid.")
        return True, None

    def evaluate_state_policy(self, financial_state: str, expected_net_value: Optional[float] = None) -> Tuple[bool, str, str]:
        """
        Evaluate if financial state and unit economics permit recovery planning.
        """
        state_upper = financial_state.upper().strip()

        if state_upper == "ALREADY_RECOVERED":
            reason = "Payment already confirmed recovered on financial ledger. Further pursuit is prohibited."
            self._record_check("STATE_AUTHORITY_POLICY", "STATE-RULE-001", False, reason)
            return False, "STOP", reason

        if state_upper == "UNCERTAIN":
            reason = "Payment is within active uncertainty/clearing window. Agent must WAIT."
            self._record_check("STATE_AUTHORITY_POLICY", "STATE-RULE-004", False, reason)
            return False, "WAIT", reason

        if state_upper == "EXCEPTION":
            reason = "Reconciliation or ledger mismatch detected. Must ESCALATE to operations."
            self._record_check("STATE_AUTHORITY_POLICY", "STATE-RULE-000", False, reason)
            return False, "ESCALATE", reason

        if state_upper == "VERIFIED_LOST":
            if expected_net_value is not None and expected_net_value <= 0:
                reason = f"Expected Net Value (Rs. {expected_net_value:.2f} <= 0) is economically irrational. Withhold pursuit."
                self._record_check("UNIT_ECONOMICS_POLICY", "POLICY-ENV-001", False, reason)
                return False, "STOP", reason
            self._record_check("STATE_AUTHORITY_POLICY", "STATE-RULE-005", True, "VERIFIED_LOST with positive ENV is eligible for recovery planning.")
            return True, "PROCEED", "Eligible for recovery planning."

        reason = f"Unknown financial state '{financial_state}'. Escalating."
        self._record_check("STATE_AUTHORITY_POLICY", "POLICY-UNKNOWN", False, reason)
        return False, "ESCALATE", reason

    def validate_action_policy(
        self,
        context: RecoveryContext,
        action: str,
        previous_actions: Optional[List[str]] = None,
        retry_count: int = 0,
    ) -> Tuple[bool, str, str]:
        """
        Deterministically validate an action against failure code policy, idempotency, and retry limits.
        """
        clean_action = action.upper().strip()
        code = (context.failure_code or context.failure_reason or "UNKNOWN").upper()
        policy = get_failure_policy(code, context.hardness)
        prev = previous_actions or []

        # 1. Prohibited action check
        prohibited_strs = [a.value for a in policy.prohibited_actions]
        if clean_action in prohibited_strs:
            reason = f"Action '{clean_action}' is explicitly prohibited for failure code '{code}' ({policy.description})."
            self._record_check("FAILURE_CODE_POLICY", f"POLICY-{code}", False, reason)
            return False, "STOP", reason

        # 2. Hard decline check
        if code in ["CARD_BLOCKED", "CARD_EXPIRED", "EXPIRED_CARD", "BAD_VPA", "INVALID_ACCOUNT"] and clean_action == "RETRY":
            reason = f"Hard decline '{code}' strictly prohibits automated RETRY."
            self._record_check("HARD_DECLINE_POLICY", "POLICY-HARD-DECLINE", False, reason)
            return False, "STOP", reason

        # 3. Retry ceiling check
        if clean_action == "RETRY" and (retry_count >= 3 or retry_count >= policy.max_retry_count):
            reason = f"Maximum retry limit ({policy.max_retry_count}) reached. Further automated retries prohibited."
            self._record_check("MAX_RETRY_POLICY", "POLICY-MAX-RETRY", False, reason)
            return False, "STOP", reason

        # 4. Duplicate action check (Idempotency)
        if clean_action in [a.upper().strip() for a in prev]:
            reason = f"Action '{clean_action}' has already been attempted on this payment. Duplicate execution blocked."
            self._record_check("IDEMPOTENCY_POLICY", "POLICY-IDEMPOTENT", False, reason)
            return False, "STOP", reason

        self._record_check("ACTION_POLICY_VALIDATION", f"POLICY-{code}", True, f"Action '{clean_action}' is permitted for '{code}'.")
        return True, "APPROVED", f"Action '{clean_action}' satisfies deterministic policies."


def validate_agent_recommendation_against_policy(
    context: RecoveryContext,
    recommendation: AgentRecommendation,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Deterministically validate the agent's proposed recommendation against policy rules.
    """
    code = context.failure_code or context.failure_reason
    policy = get_failure_policy(code, context.hardness)
    proposed = recommendation.action

    # 1. Prohibited action check
    if proposed in policy.prohibited_actions:
        return (
            False,
            "POLICY_VIOLATION",
            f"Action {proposed.value} is explicitly prohibited for failure code '{code}' ({policy.description}).",
        )

    # 2. Allowed actions list check
    if proposed not in policy.allowed_actions:
        return (
            False,
            "POLICY_VIOLATION",
            f"Action {proposed.value} is not in the permitted action set for failure code '{code}'.",
        )

    # 3. Retry count ceiling
    if proposed == RecoveryAction.RETRY and context.retry_count >= policy.max_retry_count:
        return (
            False,
            "MAX_RETRY_LIMIT",
            f"Retry count ({context.retry_count}) has reached or exceeded maximum limit ({policy.max_retry_count}).",
        )

    return (True, None, None)


def determine_policy_action(context: RecoveryContext) -> Tuple[RecoveryAction, RecoveryPriority, str, float]:
    """
    Deterministic rule-based advisor used for offline fallback or unit tests.
    """
    code = (context.failure_code or context.failure_reason or "").upper()
    hardness = (context.hardness or "").lower()
    segment = (context.customer_segment or "").lower()
    prob = context.recovery_probability or 0.5
    env = context.expected_net_value or 0.0

    prev_actions = [str(a).upper() for a in (context.previous_actions or [])]

    if hardness == "hard" or code in ["CARD_BLOCKED", "INVALID_ACCOUNT", "EXPIRED_CARD", "CARD_EXPIRED", "BAD_VPA"]:
        if env > 1000 and "PAYMENT_LINK" not in prev_actions:
            return (
                RecoveryAction.PAYMENT_LINK,
                RecoveryPriority.MEDIUM,
                f"Hard decline '{code}' cannot be retried. Sending PAYMENT_LINK to allow customer to use alternate method.",
                0.85,
            )
        return (
            RecoveryAction.ESCALATE,
            RecoveryPriority.HIGH,
            f"Hard decline '{code}' cannot be automated safely. Escalating to operations queue.",
            0.90,
        )

    if code == "INSUFFICIENT_FUNDS":
        if "PAYMENT_LINK" not in prev_actions and segment == "high_value_repeat":
            return (
                RecoveryAction.PAYMENT_LINK,
                RecoveryPriority.HIGH,
                f"INSUFFICIENT_FUNDS for high-value customer. PAYMENT_LINK provides fresh checkout session.",
                0.95,
            )
        elif "REMINDER" not in prev_actions:
            return (
                RecoveryAction.REMINDER,
                RecoveryPriority.MEDIUM,
                f"INSUFFICIENT_FUNDS detected. Gentle REMINDER avoids immediate customer friction.",
                0.88,
            )
        elif "PAYMENT_LINK" not in prev_actions:
            return (
                RecoveryAction.PAYMENT_LINK,
                RecoveryPriority.HIGH,
                f"INSUFFICIENT_FUNDS: sending direct PAYMENT_LINK checkout session.",
                0.90,
            )
        return (
            RecoveryAction.ESCALATE,
            RecoveryPriority.MEDIUM,
            f"All automated recovery actions exhausted for INSUFFICIENT_FUNDS. Escalating to support.",
            0.80,
        )

    if code in ["BANK_DOWNTIME", "TIMEOUT", "NETWORK_ERROR", "GATEWAY_ERROR"]:
        if context.retry_count < 3 and "RETRY" not in prev_actions:
            return (
                RecoveryAction.RETRY,
                RecoveryPriority.HIGH,
                f"Transient network/bank glitch '{code}'. Safe to dispatch automated RETRY.",
                0.90,
            )
        elif "PAYMENT_LINK" not in prev_actions:
            return (
                RecoveryAction.PAYMENT_LINK,
                RecoveryPriority.MEDIUM,
                f"Maximum retry limit reached or retry failed. Falling back to PAYMENT_LINK.",
                0.80,
            )
        elif "REMINDER" not in prev_actions:
            return (
                RecoveryAction.REMINDER,
                RecoveryPriority.MEDIUM,
                f"PAYMENT_LINK dispatched. Following up with REMINDER.",
                0.75,
            )
        return (
            RecoveryAction.ESCALATE,
            RecoveryPriority.MEDIUM,
            f"Automated retry and link channels exhausted. Escalating.",
            0.80,
        )

    if "PAYMENT_LINK" not in prev_actions:
        return (
            RecoveryAction.PAYMENT_LINK,
            RecoveryPriority.MEDIUM,
            f"Standard recovery action for '{code}'.",
            0.80,
        )
    elif "REMINDER" not in prev_actions:
        return (
            RecoveryAction.REMINDER,
            RecoveryPriority.MEDIUM,
            f"Follow-up reminder for '{code}'.",
            0.75,
        )
    return (
        RecoveryAction.ESCALATE,
        RecoveryPriority.MEDIUM,
        f"Exhausted automated channels for '{code}'.",
        0.80,
    )



def get_policy_hints_text(context: RecoveryContext) -> str:
    """Generate structured policy constraints text for inclusion in the LLM prompt."""
    code = context.failure_code or context.failure_reason
    policy = get_failure_policy(code, context.hardness)

    lines = [
        f"- Failure Code: {code} (Hardness: {context.hardness})",
        f"- Policy Description: {policy.description}",
        f"- Permitted Actions: {[a.value for a in policy.allowed_actions]}",
    ]
    if policy.prohibited_actions:
        lines.append(f"- PROHIBITED Actions: {[a.value for a in policy.prohibited_actions]}")
    lines.append(f"- Max Automated Retries: {policy.max_retry_count} (Current count: {context.retry_count})")
    lines.append(f"- Recommended Channel: {policy.recommended_channel}")
    return "\n".join(lines)


POLICY_HINTS: Dict[str, str] = {
    code: policy.description
    for code, policy in FAILURE_POLICY_REGISTRY.items()
}

