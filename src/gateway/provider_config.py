"""
Provider Capability Model for RecoverAI.

Defines the three provider modes:
  SIMULATION    — Deterministic mock, zero external calls (default)
  RAZORPAY_TEST — Razorpay sandbox, real API calls, no live money
  RAZORPAY_LIVE — Hard-blocked by deployment policy in this build

LIVE MODE IS INTENTIONALLY DISABLED.
RecoverAI uses Razorpay Test Mode for external integration validation.
Test Mode does not process real payments.
Live financial execution is intentionally disabled.
"""

import os
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


class ProviderMode(str, Enum):
    """Payment provider execution mode. Controls which external APIs are called."""
    SIMULATION = "simulation"
    RAZORPAY_TEST = "razorpay_test"
    RAZORPAY_LIVE = "razorpay_live"


class LiveModeDisabledError(RuntimeError):
    """
    Raised when an operation attempts RAZORPAY_LIVE mode.
    Live financial execution is intentionally disabled in this build.
    """
    pass


@dataclass
class ProviderCapabilities:
    """
    Explicit capability set for a provider mode.
    Every capability must be affirmatively declared — there is no implicit inheritance.
    """
    create_payment_link: bool = False
    fetch_payment: bool = False
    fetch_order: bool = False
    fetch_order_payments: bool = False
    capture_payment: bool = False
    send_payment_link: bool = False
    receive_webhooks: bool = False
    verify_webhook_signature: bool = False
    # LIVE MONEY EXECUTION — hard-blocked in this build
    live_money_execution: bool = False

    def supports(self, capability: str) -> bool:
        """Check whether a named capability is enabled."""
        return bool(getattr(self, capability, False))


# ---------------------------------------------------------------------------
# CAPABILITY DEFINITIONS PER MODE
# ---------------------------------------------------------------------------

_SIMULATION_CAPABILITIES = ProviderCapabilities(
    create_payment_link=True,      # Deterministic mock
    fetch_payment=True,            # Deterministic mock
    fetch_order=True,              # Deterministic mock
    fetch_order_payments=True,     # Deterministic mock
    capture_payment=False,         # Not applicable in simulation
    send_payment_link=True,        # Deterministic mock
    receive_webhooks=True,         # Mock webhooks accepted
    verify_webhook_signature=False, # No real signature in simulation
    live_money_execution=False,    # ALWAYS FALSE
)

_RAZORPAY_TEST_CAPABILITIES = ProviderCapabilities(
    create_payment_link=True,      # Real Razorpay Test API
    fetch_payment=True,            # Real Razorpay Test API
    fetch_order=True,              # Real Razorpay Test API
    fetch_order_payments=True,     # Real Razorpay Test API
    capture_payment=False,         # Not in current recovery workflow
    send_payment_link=True,        # Via Payment Links API
    receive_webhooks=True,         # Real Razorpay webhook delivery
    verify_webhook_signature=True, # HMAC-SHA256 on raw body
    live_money_execution=False,    # ALWAYS FALSE — test mode only
)

# RAZORPAY_LIVE is defined but intentionally hard-blocked at runtime.
# It exists only to give a clear capability description.
_RAZORPAY_LIVE_CAPABILITIES = ProviderCapabilities(
    create_payment_link=True,
    fetch_payment=True,
    fetch_order=True,
    fetch_order_payments=True,
    capture_payment=True,
    send_payment_link=True,
    receive_webhooks=True,
    verify_webhook_signature=True,
    live_money_execution=True,     # Declared but BLOCKED by deployment policy
)


def get_provider_mode() -> ProviderMode:
    """
    Read provider mode from RECOVERAI_PROVIDER_MODE environment variable.
    Falls back to SIMULATION if not set or unrecognised.

    Allowed values: simulation, razorpay_test, razorpay_live
    Default: simulation
    """
    raw = os.getenv("RECOVERAI_PROVIDER_MODE", "simulation").strip().lower()
    # Also support legacy PAYMENT_PROVIDER env var for backwards compat
    if raw in ("", "mock"):
        legacy = os.getenv("PAYMENT_PROVIDER", "").strip().lower()
        if legacy == "razorpay":
            raw = "razorpay_test"

    try:
        mode = ProviderMode(raw)
    except ValueError:
        logger.warning(
            "Unknown RECOVERAI_PROVIDER_MODE=%r — defaulting to SIMULATION. "
            "Allowed: simulation, razorpay_test, razorpay_live",
            raw,
        )
        mode = ProviderMode.SIMULATION

    return mode


def get_capabilities(mode: Optional[ProviderMode] = None) -> ProviderCapabilities:
    """Return the capability set for the given (or currently configured) provider mode."""
    if mode is None:
        mode = get_provider_mode()

    if mode == ProviderMode.SIMULATION:
        return _SIMULATION_CAPABILITIES
    if mode == ProviderMode.RAZORPAY_TEST:
        return _RAZORPAY_TEST_CAPABILITIES
    if mode == ProviderMode.RAZORPAY_LIVE:
        return _RAZORPAY_LIVE_CAPABILITIES

    return _SIMULATION_CAPABILITIES


def assert_live_execution_disabled(mode: Optional[ProviderMode] = None) -> None:
    """
    Hard block: raise LiveModeDisabledError if live mode is attempted.

    This is an INDEPENDENT safety guard called at multiple layers:
      - Provider factory (at adapter construction)
      - Action executor (before any gateway call)
      - API endpoint (before accepting live requests)

    It checks TWO independent conditions:
      1. provider_mode must NOT be RAZORPAY_LIVE
      2. RECOVERAI_LIVE_TRANSACTIONS env var must NOT be "true"

    Either condition alone is insufficient — both must be clear for live execution.
    In this build, live execution is always disabled regardless.
    """
    if mode is None:
        mode = get_provider_mode()

    live_flag = os.getenv("RECOVERAI_LIVE_TRANSACTIONS", "false").strip().lower()

    if mode == ProviderMode.RAZORPAY_LIVE:
        raise LiveModeDisabledError(
            "LIVE PAYMENT EXECUTION IS DISABLED. "
            "RAZORPAY_LIVE mode is blocked by deployment policy in this build. "
            "RecoverAI uses Razorpay Test Mode only. "
            "No real money movement will occur."
        )

    if live_flag == "true":
        raise LiveModeDisabledError(
            "LIVE PAYMENT EXECUTION IS DISABLED. "
            "RECOVERAI_LIVE_TRANSACTIONS=true is set but live execution "
            "requires additional deployment authorization that is not "
            "enabled in this build. No real money movement will occur."
        )


def get_provider_display_name(mode: Optional[ProviderMode] = None) -> str:
    """Return a human-readable provider name for UI display."""
    if mode is None:
        mode = get_provider_mode()

    return {
        ProviderMode.SIMULATION: "Simulation (Mock)",
        ProviderMode.RAZORPAY_TEST: "Razorpay Test Mode",
        ProviderMode.RAZORPAY_LIVE: "Razorpay Live (BLOCKED)",
    }.get(mode, "Unknown")


__all__ = [
    "ProviderMode",
    "ProviderCapabilities",
    "LiveModeDisabledError",
    "get_provider_mode",
    "get_capabilities",
    "assert_live_execution_disabled",
    "get_provider_display_name",
]
