"""
Pluggable LLM interface supporting Google Gemini, OpenRouter, and Deterministic Fallback.
Adheres strictly to the principle: The LLM is an ADVISOR; the deterministic firewall is the AUTHORITY.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
import requests
from dotenv import load_dotenv

from .models import RecoveryAction, RecoveryPriority, RecoveryContext, RecoveryPlan
from .policies import determine_policy_action

# Load environment variables
workspace_env = Path(__file__).parent.parent.parent / ".env"
if workspace_env.exists():
    load_dotenv(workspace_env)
else:
    load_dotenv()

logger = logging.getLogger("recoverai.agent.llm")

SYSTEM_INSTRUCTION = (
    "You are RecoverAI's recovery planning agent.\n"
    "You operate inside a financial safety system.\n"
    "You are an ADVISORY planner.\n"
    "You must NEVER override the Financial State Engine, Recovery Intelligence layer, or Recovery Firewall.\n"
    "You may only recommend one of:\n"
    "RETRY\n"
    "PAYMENT_LINK\n"
    "REMINDER\n"
    "WAIT\n"
    "ESCALATE\n"
    "STOP\n\n"
    "You must base your recommendation only on the supplied structured context.\n"
    "You must never claim that money was recovered unless the verification engine confirms it.\n"
    "You must never invent payment information.\n"
    "You must never recommend retrying a hard failure when policy prohibits it.\n"
    "Your purpose is to select the safest economically worthwhile recovery intervention."
)


class BaseLLMClient(ABC):
    """Abstract interface for LLM recovery planners."""

    @abstractmethod
    def generate_recovery_plan(
        self,
        context: RecoveryContext,
        allowed_actions: List[RecoveryAction],
        policy_hints: str,
    ) -> Optional[RecoveryPlan]:
        """Generate a structured RecoveryPlan from context."""
        pass


class GeminiLLMClient(BaseLLMClient):
    """
    Direct Google Gemini API implementation using the official google.genai SDK.
    """
    mode: str = "live"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.mode = "live"
        self.api_key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.client = None


        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize google.genai client: %s", e)
                self.client = None

    def generate_recovery_plan(
        self,
        context: RecoveryContext,
        allowed_actions: List[RecoveryAction],
        policy_hints: str,
    ) -> Optional[RecoveryPlan]:
        if not self.client:
            logger.info("LLM_FAILURE -> ESCALATE: Gemini client not initialized.")
            return None

        prompt = (
            f"Review this verified lost payment and select the safest recovery action.\n\n"
            f"STRUCTURED PAYMENT CONTEXT:\n"
            f"- Payment ID: {context.payment_id}\n"
            f"- Order ID: {context.order_id}\n"
            f"- Financial State: {context.financial_state}\n"
            f"- Failure Reason: {context.failure_reason}\n"
            f"- Hardness: {context.hardness}\n"
            f"- Amount: Rs. {context.amount:,.2f}\n"
            f"- Payment Method: {context.method}\n"
            f"- Customer Segment: {context.customer_segment}\n"
            f"- Recovery Probability: {context.recovery_probability}\n"
            f"- Expected Net Value: Rs. {context.expected_net_value}\n"
            f"- Previous Attempts: {context.previous_attempts}\n"
            f"- Retry Count: {context.retry_count}\n\n"
            f"POLICY CONSTRAINTS:\n{policy_hints}\n\n"
            f"ALLOWED ACTIONS: {[a.value for a in allowed_actions]}\n\n"
            f"Respond ONLY with valid JSON in this exact structure:\n"
            f"{{\n"
            f'  "action": "PAYMENT_LINK | RETRY | REMINDER | WAIT | ESCALATE | STOP",\n'
            f'  "priority": "LOW | MEDIUM | HIGH | CRITICAL",\n'
            f'  "reason": "<Detailed rationale for why this is the safest action>",\n'
            f'  "confidence": <float between 0.0 and 1.0>\n'
            f"}}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "temperature": 0.1,
                    "response_mime_type": "application/json",
                },
            )

            raw_text = response.text.strip()
            data = json.loads(raw_text)

            action_str = str(data.get("action", "")).upper()
            if action_str not in [a.value for a in allowed_actions]:
                logger.warning("LLM_FAILURE -> ESCALATE: Gemini returned invalid action: %s", action_str)
                return None

            action_enum = RecoveryAction(action_str)
            priority_str = str(data.get("priority", "MEDIUM")).upper()
            priority_enum = RecoveryPriority[priority_str] if priority_str in RecoveryPriority.__members__ else RecoveryPriority.MEDIUM
            reason_text = str(data.get("reason", "Advisory recommendation from Gemini planner."))
            confidence_val = float(data.get("confidence", 0.85))
            confidence_clamped = max(0.0, min(1.0, confidence_val))

            return RecoveryPlan(
                payment_id=context.payment_id,
                action=action_enum,
                priority=priority_enum,
                reason=reason_text,
                confidence=confidence_clamped,
                expected_net_value=context.expected_net_value if context.expected_net_value is not None else 0.0,
            )

        except Exception as err:
            logger.warning("LLM_FAILURE -> ESCALATE: Gemini API call failed: %s", err)
            return None


class OpenRouterLLMClient(BaseLLMClient):
    """
    OpenRouter API client supporting multi-model routing.
    """
    mode: str = "live"

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.mode = "live"
        self.api_key = api_key if api_key is not None else os.getenv("OPENROUTER_API_KEY")
        self.model_name = model_name or os.getenv("OPENROUTER_MODEL", "google/gemini-2.5-flash")


    def generate_recovery_plan(
        self,
        context: RecoveryContext,
        allowed_actions: List[RecoveryAction],
        policy_hints: str,
    ) -> Optional[RecoveryPlan]:
        if not self.api_key or not self.api_key.strip():
            logger.info("LLM_FAILURE -> ESCALATE: OpenRouter API key not configured.")
            return None

        prompt = (
            f"Review this verified lost payment and select the safest recovery action.\n\n"
            f"STRUCTURED PAYMENT CONTEXT:\n"
            f"- Payment ID: {context.payment_id}\n"
            f"- Order ID: {context.order_id}\n"
            f"- Financial State: {context.financial_state}\n"
            f"- Failure Reason: {context.failure_reason}\n"
            f"- Hardness: {context.hardness}\n"
            f"- Amount: Rs. {context.amount:,.2f}\n"
            f"- Payment Method: {context.method}\n"
            f"- Customer Segment: {context.customer_segment}\n"
            f"- Recovery Probability: {context.recovery_probability}\n"
            f"- Expected Net Value: Rs. {context.expected_net_value}\n"
            f"- Previous Attempts: {context.previous_attempts}\n"
            f"- Retry Count: {context.retry_count}\n\n"
            f"POLICY CONSTRAINTS:\n{policy_hints}\n\n"
            f"ALLOWED ACTIONS: {[a.value for a in allowed_actions]}\n\n"
            f"Respond ONLY with valid JSON in this exact structure:\n"
            f"{{\n"
            f'  "action": "PAYMENT_LINK | RETRY | REMINDER | WAIT | ESCALATE | STOP",\n'
            f'  "priority": "LOW | MEDIUM | HIGH | CRITICAL",\n'
            f'  "reason": "<Detailed rationale for why this is the safest action>",\n'
            f'  "confidence": <float between 0.0 and 1.0>\n'
            f"}}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://recoverai.io",
            "X-Title": "RecoverAI",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 400,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10,
            )

            if resp.status_code != 200:
                logger.warning("LLM_FAILURE -> ESCALATE: OpenRouter error %d: %s", resp.status_code, resp.text)
                return None

            data_resp = resp.json()
            raw_text = data_resp["choices"][0]["message"]["content"].strip()
            data = json.loads(raw_text)

            action_str = str(data.get("action", "")).upper()
            if action_str not in [a.value for a in allowed_actions]:
                logger.warning("LLM_FAILURE -> ESCALATE: OpenRouter returned invalid action: %s", action_str)
                return None

            action_enum = RecoveryAction(action_str)
            priority_str = str(data.get("priority", "MEDIUM")).upper()
            priority_enum = RecoveryPriority[priority_str] if priority_str in RecoveryPriority.__members__ else RecoveryPriority.MEDIUM
            reason_text = str(data.get("reason", "Advisory recommendation from OpenRouter planner."))
            confidence_val = float(data.get("confidence", 0.85))
            confidence_clamped = max(0.0, min(1.0, confidence_val))

            return RecoveryPlan(
                payment_id=context.payment_id,
                action=action_enum,
                priority=priority_enum,
                reason=reason_text,
                confidence=confidence_clamped,
                expected_net_value=context.expected_net_value if context.expected_net_value is not None else 0.0,
            )

        except Exception as err:
            logger.warning("LLM_FAILURE -> ESCALATE: OpenRouter request failed: %s", err)
            return None


class DeterministicFallbackLLMClient(BaseLLMClient):
    """
    Deterministic rule-based advisor used when LLMs are offline, disabled, or for fast unit testing.
    """
    mode: str = "demo"

    def generate_recovery_plan(
        self,
        context: RecoveryContext,
        allowed_actions: List[RecoveryAction],
        policy_hints: str,
    ) -> Optional[RecoveryPlan]:
        action, priority, reason, confidence = determine_policy_action(context)
        return RecoveryPlan(
            payment_id=context.payment_id,
            action=action,
            priority=priority,
            reason=reason,
            confidence=confidence,
            expected_net_value=context.expected_net_value if context.expected_net_value is not None else 0.0,
        )


def get_default_llm_client() -> BaseLLMClient:
    """
    Factory returning appropriate LLM client based on AI_MODE.
    - AI_MODE=demo: Returns DeterministicFallbackLLMClient (no external calls, 100% offline).
    - AI_MODE=live: Returns OpenRouterLLMClient or GeminiLLMClient if configured, otherwise falls back safely.
    """
    ai_mode = os.getenv("AI_MODE", "demo").lower().strip()
    if ai_mode == "demo":
        return DeterministicFallbackLLMClient()

    provider = os.getenv("LLM_PROVIDER", "").lower()
    
    if provider == "gemini":
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("your_key") and gemini_key.strip():
            client = GeminiLLMClient(api_key=gemini_key)
            if client.client is not None:
                return client

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key and openrouter_key.strip():
        return OpenRouterLLMClient(api_key=openrouter_key)

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and not gemini_key.startswith("your_key") and gemini_key.strip():
        client = GeminiLLMClient(api_key=gemini_key)
        if client.client is not None:
            return client

    return DeterministicFallbackLLMClient()
