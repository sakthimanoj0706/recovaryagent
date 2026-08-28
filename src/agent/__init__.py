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
from .schemas import (
    AgentAction,
    AgentStepStage,
    AgentStepRecord,
    AgentRunResult,
    ToolCallRecord,
    PolicyCheckRecord,
    AgentPlanResponse,
)
from .memory import AgentMemory, ActionAttemptMemory
from .tools import RecoveryToolRegistry
from .policy import (
    PolicyEngine,
    FailurePolicy,
    FAILURE_POLICY_REGISTRY,
    get_failure_policy,
    validate_agent_recommendation_against_policy,
    determine_policy_action,
    get_policy_hints_text,
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
from .orchestrator import AgenticRecoveryOrchestrator, RecoverAIOrchestrator
from .trace import AgentDecisionTrace, build_decision_trace

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
    "AgentAction",
    "AgentStepStage",
    "AgentStepRecord",
    "AgentRunResult",
    "ToolCallRecord",
    "PolicyCheckRecord",
    "AgentPlanResponse",
    "AgentMemory",
    "ActionAttemptMemory",
    "RecoveryToolRegistry",
    "PolicyEngine",
    "FailurePolicy",
    "FAILURE_POLICY_REGISTRY",
    "get_failure_policy",
    "validate_agent_recommendation_against_policy",
    "determine_policy_action",
    "get_policy_hints_text",
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
    "AgenticRecoveryOrchestrator",
    "RecoverAIOrchestrator",
    "AgentDecisionTrace",
    "build_decision_trace",
]
