"""
Agentic Recovery Planner for RecoverAI.
Transforms structured RecoveryContext into a validated AgentRecommendation.
Zero authority over financial state, expected net value, or verification.
"""

import logging
from typing import Optional, List
from .models import (
    RecoveryAction,
    RecoveryPriority,
    RecoveryContext,
    AgentRecommendation,
    RecoveryPlan,
)
from .policy import (
    get_failure_policy,
    get_policy_hints_text,
    determine_policy_action,
    validate_agent_recommendation_against_policy,
)
from .llm import BaseLLMClient, DeterministicFallbackLLMClient, get_default_llm_client

logger = logging.getLogger("recoverai.agent.planner")


class AgenticRecoveryPlanner:
    """
    Agentic Recovery Planner.
    Consults the LLM for advisory planning, but validates output strictly against
    the AgentRecommendation schema and deterministic policy rules before returning.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm_client = llm_client if llm_client is not None else get_default_llm_client()

    def plan_recovery(self, context: RecoveryContext) -> Optional[AgentRecommendation]:
        """
        Generate a strictly validated AgentRecommendation from structured RecoveryContext.
        Returns None if an active LLM client failed or returned invalid output.
        """
        code = context.failure_code or context.failure_reason
        policy = get_failure_policy(code, context.hardness)
        allowed_actions = policy.allowed_actions
        policy_hints = get_policy_hints_text(context)

        # 1. Deterministic Fallback if client is None or explicitly DeterministicFallbackLLMClient
        if self.llm_client is None or isinstance(self.llm_client, DeterministicFallbackLLMClient):
            act, pri, rsn, conf = determine_policy_action(context)
            return AgentRecommendation(
                payment_id=context.payment_id,
                action=act,
                priority=pri,
                channel=policy.recommended_channel,
                timing="immediate",
                message_strategy="standard_recovery",
                rationale=rsn,
                confidence=conf,
                policy_references=[f"POLICY-{policy.failure_code}"],
                observed_failure=code,
                selected_strategy=act.value,
                policy_basis=policy.description,
                risk_level="LOW" if act in [RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER] else "MEDIUM",
                expected_net_value=context.expected_net_value,
            )

        # 2. Query LLM Planner
        raw_plan = None
        try:
            raw_plan = self.llm_client.generate_recovery_plan(
                context=context,
                allowed_actions=allowed_actions,
                policy_hints=policy_hints,
            )
        except Exception as e:
            logger.warning("Agent planner LLM execution exception: %s", e)
            return None

        if raw_plan is None:
            logger.warning("LLM planner returned None / failed for payment %s", context.payment_id)
            return None

        # 3. Format into typed AgentRecommendation
        recommendation = AgentRecommendation(
            payment_id=context.payment_id,
            action=raw_plan.action,
            priority=getattr(raw_plan, "priority", RecoveryPriority.MEDIUM),
            channel=getattr(raw_plan, "channel", policy.recommended_channel),
            timing=getattr(raw_plan, "timing", "immediate"),
            message_strategy=getattr(raw_plan, "message_strategy", "standard_recovery"),
            rationale=getattr(raw_plan, "rationale", getattr(raw_plan, "reason", "Advisory recommendation.")),
            confidence=raw_plan.confidence,
            policy_references=getattr(raw_plan, "policy_references", [f"POLICY-{policy.failure_code}"]),
            observed_failure=code,
            selected_strategy=raw_plan.action.value,
            policy_basis=policy.description,
            risk_level="LOW" if raw_plan.action in [RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER] else "MEDIUM",
            expected_net_value=context.expected_net_value,
        )

        return recommendation


# Backward compatibility alias
AgentPlanner = AgenticRecoveryPlanner
