import re

with open('src/agent/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add imports
imports = '''
from intelligence.service import IntelligentRecoveryService
from intelligence.models import IntelligentDecision
'''
content = content.replace('from .trace import AgentDecisionTrace, build_decision_trace', 'from .trace import AgentDecisionTrace, build_decision_trace\n' + imports)

# Add to __init__
init_patch = '''
        self.verifier = verifier or RecoveryVerifier(state_engine=self.state_engine)
        self.audit_logger = audit_logger or AuditLogger()
        self.intelligence_service = IntelligentRecoveryService(model=model, llm_client=llm_client)
'''
content = content.replace('self.verifier = verifier or RecoveryVerifier(state_engine=self.state_engine)\n        self.audit_logger = audit_logger or AuditLogger()', init_patch)

# Add strategy_mode parameter to run_recovery_agent
content = content.replace('multi_step_scenario: Optional[bool] = False,\n    ) -> AgentRunResult:', 'multi_step_scenario: Optional[bool] = False,\n        strategy_mode: str = "INTELLIGENT",\n    ) -> AgentRunResult:')

# Patch B. REASON & C. PLAN
plan_patch = '''
            # B. REASON & C. PLAN (Intelligent Recovery Engine)
            if strategy_mode in ["INTELLIGENT", "DETERMINISTIC"]:
                decision = self.intelligence_service.decide(payment, current_events, memory.retry_count)
                
                # If deterministic mode, override selected action with deterministic best
                if strategy_mode == "DETERMINISTIC":
                    try:
                        action = RecoveryAction(decision.deterministic_best_action.action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = f"DETERMINISTIC MODE: Chose {action.value}."
                    confidence = 1.0
                else:
                    try:
                        action = RecoveryAction(decision.selected_action)
                    except ValueError:
                        action = RecoveryAction.STOP
                    reason = decision.selection_reason
                    confidence = decision.llm_recommendation.confidence if decision.llm_recommendation else 1.0
            else:
                # NAIVE MODE or legacy
                recommendation = self.planner.plan_recovery(ctx)
                if recommendation is None:
                    action = RecoveryAction.ESCALATE
                    reason = "LLM unavailable"
                    confidence = 0.0
                else:
                    action = recommendation.action
                    reason = recommendation.rationale
                    confidence = recommendation.confidence
'''

# We need to accurately replace the block
pattern = re.compile(r'# B\. REASON & C\. PLAN \(Advisory LLM Planner\).*?last_confidence = confidence', re.DOTALL)
replacement = plan_patch + '''
            last_agent_action = action.value
            last_agent_reason = reason
            last_confidence = confidence
'''
content = pattern.sub(replacement, content)

with open('src/agent/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)
