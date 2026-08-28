"""
Deterministic Policy Registry and Validation Engine for RecoverAI.
Guarantees that the LLM cannot propose actions that violate fintech safety policies.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from .models import RecoveryAction, RecoveryPriority, RecoveryContext, AgentRecommendation


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


def validate_agent_recommendation_against_policy(
    context: RecoveryContext,
    recommendation: AgentRecommendation,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Deterministically validate the agent's proposed recommendation against policy rules.
    Returns:
        (is_valid, violation_code, violation_reason)
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

    if hardness == "hard" or code in ["CARD_BLOCKED", "INVALID_ACCOUNT", "EXPIRED_CARD"]:
        if env > 1000:
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
        if segment == "high_value_repeat":
            return (
                RecoveryAction.PAYMENT_LINK,
                RecoveryPriority.HIGH,
                f"INSUFFICIENT_FUNDS for high-value customer. PAYMENT_LINK provides fresh checkout session.",
                0.95,
            )
        return (
            RecoveryAction.REMINDER,
            RecoveryPriority.MEDIUM,
            f"INSUFFICIENT_FUNDS detected. Gentle REMINDER avoids immediate friction.",
            0.80,
        )

    if code in ["TIMEOUT", "BANK_DOWNTIME", "NETWORK_ERROR", "GATEWAY_ERROR"]:
        if context.retry_count >= 3:
            return (
                RecoveryAction.PAYMENT_LINK,
                RecoveryPriority.HIGH,
                f"Maximum retry limit reached. Falling back to PAYMENT_LINK.",
                0.85,
            )
        return (
            RecoveryAction.RETRY,
            RecoveryPriority.HIGH,
            f"Transient '{code}' failure. Safe to RETRY under policy limit (attempt {context.retry_count + 1}).",
            0.90,
        )

    return (
        RecoveryAction.PAYMENT_LINK,
        RecoveryPriority.MEDIUM,
        "Standard recovery workflow: PAYMENT_LINK dispatched.",
        0.80,
    )


def get_policy_hints_text(context: RecoveryContext) -> str:
    """Generate textual policy constraints for prompt injection."""
    code = context.failure_code or context.failure_reason
    policy = get_failure_policy(code, context.hardness)
    allowed_str = ", ".join(a.value for a in policy.allowed_actions)
    prohibited_str = ", ".join(a.value for a in policy.prohibited_actions) if policy.prohibited_actions else "None"

    return (
        f"- Failure Policy for '{policy.failure_code}':\n"
        f"  • Allowed Actions: {allowed_str}\n"
        f"  • Prohibited Actions: {prohibited_str}\n"
        f"  • Recommended Channel: {policy.recommended_channel}\n"
        f"  • Max Retry Limit: {policy.max_retry_count}\n"
        f"  • Policy Directive: {policy.description}"
    )


# Compatibility aliases
POLICY_HINTS = {k: v.description for k, v in FAILURE_POLICY_REGISTRY.items()}
