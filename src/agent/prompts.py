"""
System instructions and prompts for RecoverAI Agentic Recovery Planner.
Emphasizes bounded advisory role: The LLM suggests HOW to recover, but has ZERO authority over financial truth.
"""

from typing import List
from .models import RecoveryContext

AGENTIC_SYSTEM_INSTRUCTION = (
    "You are RecoverAI's Agentic Recovery Planner.\n"
    "You operate inside a mission-critical fintech safety system.\n"
    "You are an ADVISORY planner. You recommend HOW to recover a financially verified lost payment.\n\n"
    "CRITICAL CONSTRAINTS & NON-NEGOTIABLE BOUNDARIES:\n"
    "1. You have ZERO authority over financial truth. You cannot alter the financial state.\n"
    "2. You have ZERO authority over unit economics. You cannot alter expected net value or recovery probability.\n"
    "3. You cannot bypass the deterministic Recovery Firewall.\n"
    "4. You cannot declare a payment recovered.\n"
    "5. You must choose ONLY from permitted actions: RETRY, PAYMENT_LINK, REMINDER, ESCALATE, STOP.\n"
    "6. Never recommend retrying a hard failure (e.g., CARD_BLOCKED, INVALID_ACCOUNT, USER_CANCELLED).\n"
    "7. For INSUFFICIENT_FUNDS, choose PAYMENT_LINK or REMINDER.\n"
    "8. For BANK_DOWNTIME or TIMEOUT, choose RETRY or PAYMENT_LINK.\n"
    "9. Base your decision ONLY on the provided structured context.\n"
    "10. Output MUST be strictly valid JSON matching the specified schema."
)


def build_planner_prompt(
    context: RecoveryContext,
    allowed_actions: List[str],
    policy_hints: str,
) -> str:
    """
    Format a structured prompt for the LLM planner.
    """
    return (
        f"Review this verified lost payment and select the safest, most effective recovery action.\n\n"
        f"STRUCTURED PAYMENT CONTEXT:\n"
        f"- Payment ID: {context.payment_id}\n"
        f"- Order ID: {context.order_id or 'N/A'}\n"
        f"- Financial State: {context.financial_state}\n"
        f"- Failure Reason / Code: {context.failure_code or context.failure_reason}\n"
        f"- Failure Description: {context.failure_description or 'None'}\n"
        f"- Hardness: {context.hardness}\n"
        f"- Amount: Rs. {context.amount:,.2f}\n"
        f"- Payment Method: {context.method or 'unknown'}\n"
        f"- Customer Segment: {context.customer_segment or 'unknown'}\n"
        f"- Recovery Probability: {context.recovery_probability}\n"
        f"- Expected Net Value: Rs. {context.expected_net_value}\n"
        f"- Previous Attempts: {context.previous_attempts}\n"
        f"- Retry Count: {context.retry_count}\n\n"
        f"DETERMINISTIC POLICY CONSTRAINTS:\n"
        f"{policy_hints}\n\n"
        f"ALLOWED ACTIONS FOR THIS CONTEXT: {allowed_actions}\n\n"
        f"Respond ONLY with valid JSON in this exact structure:\n"
        f"{{\n"
        f'  "action": "PAYMENT_LINK | RETRY | REMINDER | ESCALATE | STOP",\n'
        f'  "channel": "whatsapp | sms | email | gateway | none",\n'
        f'  "timing": "immediate | delayed_15m | backoff_exponential",\n'
        f'  "message_strategy": "A brief note on customer messaging tone (e.g. polite_reminder, alternative_method)",\n'
        f'  "rationale": "Clear non-empty rationale explaining why this is the safest and most effective action",\n'
        f'  "confidence": 0.85,\n'
        f'  "policy_references": ["POLICY-001"],\n'
        f'  "observed_failure": "{context.failure_code or context.failure_reason}",\n'
        f'  "selected_strategy": "<Brief summary of strategy>",\n'
        f'  "policy_basis": "<Policy rationale>",\n'
        f'  "risk_level": "LOW | MEDIUM | HIGH"\n'
        f"}}"
    )
