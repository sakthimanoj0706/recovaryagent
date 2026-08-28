"""
Lightweight, bounded working memory for RecoverAI Agentic Recovery Orchestrator.

CRITICAL INVARIANT:
Memory is an operational scratchpad for multi-step replanning.
Memory must NEVER become the financial source of truth.
The Financial State Engine remains the sole authority.
"""

from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict
from .schemas import AgentAction


class ActionAttemptMemory(BaseModel):
    """Immutable log of an action attempt in the working memory."""
    model_config = ConfigDict(extra="allow")

    step_number: int
    action: str
    firewall_decision: str
    execution_status: str
    verification_state: str
    final_result: str
    reason: Optional[str] = None
    timestamp: Optional[str] = None


class AgentMemory(BaseModel):
    """
    Bounded working memory for an autonomous recovery session.
    Tracks previous actions and outcomes to enable intelligent replanning without duplicate loops.
    """
    model_config = ConfigDict(extra="allow")

    payment_id: str
    previous_actions: List[str] = Field(default_factory=list)
    previous_outcomes: List[str] = Field(default_factory=list)
    action_history: List[ActionAttemptMemory] = Field(default_factory=list)
    retry_count: int = 0
    last_verification_state: Optional[str] = None
    previous_agent_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    firewall_blocks: List[Dict[str, Any]] = Field(default_factory=list)
    failed_actions: Set[str] = Field(default_factory=set)

    def record_attempt(
        self,
        step_number: int,
        action: str,
        firewall_decision: str,
        execution_status: str,
        verification_state: str,
        final_result: str,
        reason: Optional[str] = None,
    ) -> None:
        """Record an action attempt and update working memory counters."""
        self.previous_actions.append(action)
        self.previous_outcomes.append(final_result)
        self.last_verification_state = verification_state

        attempt = ActionAttemptMemory(
            step_number=step_number,
            action=action,
            firewall_decision=firewall_decision,
            execution_status=execution_status,
            verification_state=verification_state,
            final_result=final_result,
            reason=reason,
        )
        self.action_history.append(attempt)

        if action == AgentAction.RETRY.value:
            self.retry_count += 1

        if final_result in ["RECOVERY_FAILED", "SAFE_STOP", "DUPLICATE_ACTION_BLOCKED"]:
            self.failed_actions.add(action)

        if firewall_decision == "STOP":
            self.firewall_blocks.append({
                "step": step_number,
                "action": action,
                "reason": reason,
            })

    def has_action_been_attempted(self, action: str) -> bool:
        """Check if an action has already been attempted in this session."""
        return action.upper().strip() in [a.upper().strip() for a in self.previous_actions]

    def has_action_failed(self, action: str) -> bool:
        """Check if an action was previously executed and failed recovery."""
        return action.upper().strip() in [a.upper().strip() for a in self.failed_actions]

    def get_failed_actions_list(self) -> List[str]:
        """Return list of actions that have failed recovery verification."""
        return list(self.failed_actions)

    def is_max_retries_reached(self, max_limit: int = 3) -> bool:
        """Check if maximum retry threshold has been reached."""
        return self.retry_count >= max_limit

    def to_snapshot(self) -> Dict[str, Any]:
        """Export serialized dictionary snapshot of working memory."""
        return {
            "payment_id": self.payment_id,
            "previous_actions": list(self.previous_actions),
            "previous_outcomes": list(self.previous_outcomes),
            "retry_count": self.retry_count,
            "last_verification_state": self.last_verification_state,
            "failed_actions": list(self.failed_actions),
            "firewall_blocks_count": len(self.firewall_blocks),
            "total_attempts": len(self.action_history),
        }
