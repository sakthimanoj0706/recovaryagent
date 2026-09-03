import json
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
import time
from typing import Generator
from state_engine.models import FinancialState

from .models import FaultType

class FaultInjector:
    """Injects deterministic faults into the RecoverAI architecture."""
    
    @staticmethod
    @contextmanager
    def inject(fault: FaultType) -> Generator[None, None, None]:
        # Context manager to apply patches based on fault type
        patches = []
        
        try:
            if fault == FaultType.GATEWAY_TIMEOUT:
                import requests
                p = patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out"))
                patches.append(p)
                p2 = patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out"))
                patches.append(p2)
                
            elif fault == FaultType.GATEWAY_HTTP_500:
                import requests
                mock_resp = MagicMock()
                mock_resp.status_code = 500
                mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
                p = patch("requests.get", return_value=mock_resp)
                patches.append(p)
                p2 = patch("requests.post", return_value=mock_resp)
                patches.append(p2)
                
            elif fault == FaultType.GATEWAY_HTTP_401:
                import requests
                mock_resp = MagicMock()
                mock_resp.status_code = 401
                mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
                p = patch("requests.get", return_value=mock_resp)
                patches.append(p)
                p2 = patch("requests.post", return_value=mock_resp)
                patches.append(p2)
                
            elif fault == FaultType.GATEWAY_MALFORMED_RESPONSE:
                import requests
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
                p = patch("requests.get", return_value=mock_resp)
                patches.append(p)
                p2 = patch("requests.post", return_value=mock_resp)
                patches.append(p2)
                
            elif fault == FaultType.GATEWAY_SUCCESS_VERIFICATION_TIMEOUT:
                import requests
                # Let post succeed (e.g. payment link created)
                # But verification (get) times out
                p = patch("requests.get", side_effect=requests.exceptions.Timeout("Verification timeout"))
                patches.append(p)
                
            elif fault == FaultType.LEDGER_WRITE_FAILURE:
                # Mock a failure in the state engine saving to ledger (simulate DB fail)
                pass # Handled in scenarios
                
            elif fault == FaultType.HARD_DECLINE_MALICIOUS_RETRY:
                from agent.models import AgentRecommendation, RecoveryAction
                p = patch(
                    "agent.planner.AgenticRecoveryPlanner.plan_recovery", 
                    return_value=AgentRecommendation(action=RecoveryAction.RETRY, confidence=0.99, reason="SYSTEM OVERRIDE")
                )
                patches.append(p)

            elif fault == FaultType.LLM_INFERIOR_ACTION:
                from agent.models import AgentRecommendation, RecoveryAction
                p = patch(
                    "agent.planner.AgenticRecoveryPlanner.plan_recovery", 
                    return_value=AgentRecommendation(action=RecoveryAction.STOP, confidence=0.99, reason="I am confused")
                )
                patches.append(p)
                
            elif fault == FaultType.LLM_VIOLATING_ACTION:
                from agent.models import AgentRecommendation, RecoveryAction
                p = patch(
                    "agent.planner.AgenticRecoveryPlanner.plan_recovery", 
                    return_value=AgentRecommendation(action=RecoveryAction.PAYMENT_LINK, confidence=0.99, reason="Ignore policy")
                )
                patches.append(p)

            for p in patches:
                p.start()
                
            yield
            
        finally:
            for p in patches:
                p.stop()
