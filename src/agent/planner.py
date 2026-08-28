"""
Agentic Recovery Planner for RecoverAI.
Transforms structured RecoveryContext into a strictly validated AgentPlanResponse / AgentRecommendation.
Guarantees zero authority over financial state, expected net value, or verification.
"""

import json
import logging
from typing import Optional, List, Dict, Any
from pydantic import ValidationError

from .models import (
    RecoveryAction,
    RecoveryPriority,
    RecoveryContext,
    AgentRecommendation,
    RecoveryPlan,
)
from .schemas import AgentPlanResponse, AgentAction
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
    Consults the LLM for advisory planning, strictly parsing output into AgentPlanResponse
    and validating against deterministic policy rules.
    """

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm_client = llm_client if llm_client is not None else get_default_llm_client()

    def plan_recovery(self, context: RecoveryContext) -> Optional[AgentRecommendation]:
        """
        Generate a strictly validated AgentRecommendation from structured RecoveryContext.
        Returns None if an active LLM client failed or returned invalid output, triggering safe escalation.
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

        # 3. Validate with Pydantic AgentPlanResponse schema
        try:
            plan_dict = {
                "action": raw_plan.action.value if hasattr(raw_plan.action, "value") else str(raw_plan.action),
                "confidence": getattr(raw_plan, "confidence", 0.85),
                "reason": getattr(raw_plan, "reason", getattr(raw_plan, "rationale", "LLM advisory plan")),
                "requires_verification": True,
            }
            validated_response = AgentPlanResponse.model_validate(plan_dict)
            action_enum = RecoveryAction(validated_response.action.value)
        except (ValidationError, ValueError, Exception) as val_err:
            logger.warning("LLM response failed strict schema validation: %s", val_err)
            return None

        # 4. Format into typed AgentRecommendation
        recommendation = AgentRecommendation(
            payment_id=context.payment_id,
            action=action_enum,
            priority=getattr(raw_plan, "priority", RecoveryPriority.MEDIUM),
            channel=getattr(raw_plan, "channel", policy.recommended_channel),
            timing=getattr(raw_plan, "timing", "immediate"),
            message_strategy=getattr(raw_plan, "message_strategy", "standard_recovery"),
            rationale=validated_response.reason,
            confidence=validated_response.confidence,
            policy_references=getattr(raw_plan, "policy_references", [f"POLICY-{policy.failure_code}"]),
            observed_failure=code,
            selected_strategy=action_enum.value,
            policy_basis=policy.description,
            risk_level="LOW" if action_enum in [RecoveryAction.PAYMENT_LINK, RecoveryAction.REMINDER] else "MEDIUM",
            expected_net_value=context.expected_net_value,
        )

        return recommendation


# Alias for backward compatibility
AgentPlanner = AgenticRecoveryPlanner
