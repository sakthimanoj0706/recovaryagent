"""
RecoverAI Agentic Recovery Planner & Closed-Loop Verification package.
"""

from .models import (
    RecoveryAction,
    RecoveryPriority,
    FirewallDecision,
    AgentResultType,
    RecoveryContext,
    AgentRecommendation,
    RecoveryPlan,
    FirewallResult,
    AgentExecutionResult,
)
from .tools import RecoveryToolRegistry
from .policy import (
    FailurePolicy,
    FAILURE_POLICY_REGISTRY,
    get_failure_policy,
    validate_agent_recommendation_against_policy,
    determine_policy_action,
    get_policy_hints_text,
    POLICY_HINTS,
)
from .prompts import AGENTIC_SYSTEM_INSTRUCTION, build_planner_prompt
from .firewall import RecoveryFirewall
from .audit import AuditLogger
from .llm import (
    BaseLLMClient,
    GeminiLLMClient,
    OpenRouterLLMClient,
    DeterministicFallbackLLMClient,
    get_default_llm_client,
)
from .planner import AgenticRecoveryPlanner, AgentPlanner
from .orchestrator import RecoverAIOrchestrator, RecoveryOrchestrator, run_recovery_agent

__all__ = [
    "RecoveryAction",
    "RecoveryPriority",
    "FirewallDecision",
    "AgentResultType",
    "RecoveryContext",
    "AgentRecommendation",
    "RecoveryPlan",
    "FirewallResult",
    "AgentExecutionResult",
    "RecoveryToolRegistry",
    "FailurePolicy",
    "FAILURE_POLICY_REGISTRY",
    "get_failure_policy",
    "validate_agent_recommendation_against_policy",
    "determine_policy_action",
    "get_policy_hints_text",
    "POLICY_HINTS",
    "AGENTIC_SYSTEM_INSTRUCTION",
    "build_planner_prompt",
    "RecoveryFirewall",
    "AuditLogger",
    "BaseLLMClient",
    "GeminiLLMClient",
    "OpenRouterLLMClient",
    "DeterministicFallbackLLMClient",
    "get_default_llm_client",
    "AgenticRecoveryPlanner",
    "AgentPlanner",
    "RecoverAIOrchestrator",
    "RecoveryOrchestrator",
    "run_recovery_agent",
]
