"""
RecoverAI - Agentic Recovery Planner & Recovery Firewall Interactive Demo.

Demonstrates 4 core operational scenarios with Google Gemini integration:
1. Standard Successful Closed-Loop Recovery Path
2. False Recovery Prevention (FAILED != LOST)
3. Economically Irrational Recovery Prevention (Negative ENV)
4. Hard Failure Safety Rule (Firewall blocks unsafe RETRY)
"""

import sys
import json
from pathlib import Path

# Ensure safe UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from state_engine.models import PaymentRecord, Event
from recovery.model import RecoveryProbabilityModel
from agent.models import RecoveryAction
from agent.orchestrator import RecoveryOrchestrator
from agent.llm import get_default_llm_client


def print_agent_decision_card(result):
    prob_str = f"{result.recovery_probability:.2f}" if result.recovery_probability is not None else "N/A"
    env_str = f"Rs. {result.expected_net_value:,.2f}" if result.expected_net_value is not None else "N/A"

    print("========================================")
    print("        RECOVERAI AGENT")
    print("========================================")
    print(f"Payment             : {result.payment_id}")
    print(f"Financial State     : {result.financial_state}")
    print(f"Recovery Probability: {prob_str}")
    print(f"Expected Net Value  : {env_str}")
    print()
    print("---------- AGENT ----------")
    print(f"Recommended Action  : {result.agent_action.value}")
    print(f"Reason              : {result.agent_reason}")
    print(f"Confidence          : {result.confidence:.2f}")
    print()
    print("---------- FIREWALL --------")
    print(f"Decision            : {result.firewall_decision.value}")
    print(f"Rule                : {result.firewall_rule or 'None (Passed all rules)'}")
    print(f"Reason              : {result.firewall_reason}")
    print()
    print("---------- EXECUTION -------")
    print(f"Status              : {result.execution_status}")
    if result.execution_detail:
        print(f"Detail              : {result.execution_detail.get('message', '')}")
    print()
    print("---------- VERIFICATION ----")
    print(f"Final State         : {result.verification_state or 'N/A'}")
    print()
    print("---------- RESULT ----------")
    print(f"Outcome             : {result.final_result}")
    print("========================================\n")


def run_demo():
    print("*" * 80)
    print(" RecoverAI — AGENTIC RECOVERY PLANNER & FIREWALL DEMO ")
    print(" 'Prove the money. Prioritize the chase. Recover it.' ")
    print("*" * 80 + "\n")

    model_path = Path("models") / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    llm_client = get_default_llm_client()
    orchestrator = RecoveryOrchestrator(llm_client=llm_client, model=model)

    # -------------------------------------------------------------------------
    # SCENARIO 1: SUCCESSFUL RECOVERY PATH
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print(" SCENARIO 1: SUCCESSFUL RECOVERY PATH")
    print(" Soft Failure -> Positive ENV -> Agent Plan -> Firewall Approved -> Simulated Action -> Recovered")
    print("=" * 80)
    pay1 = PaymentRecord(
        payment_id="pay_demo_001",
        order_id="order_demo_001",
        amount=10000.0,
        method="upi",
        customer_segment="high_value_repeat",
    )
    events1 = [
        Event(event="payment.created", payment_id="pay_demo_001", order_id="order_demo_001", ts="2026-08-10T10:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_001", order_id="order_demo_001", error_code="INSUFFICIENT_FUNDS", hardness="soft", ts="2026-08-10T10:00:06Z"),
    ]
    post_events1 = [
        Event(event="payment.authorized", payment_id="pay_demo_001", order_id="order_demo_001", ts="2026-08-10T10:15:00Z"),
        Event(event="payment.captured", payment_id="pay_demo_001", order_id="order_demo_001", ts="2026-08-10T10:15:05Z"),
    ]
    res1 = orchestrator.run_lifecycle(pay1, events1, post_action_events=post_events1)
    print_agent_decision_card(res1)

    # -------------------------------------------------------------------------
    # SCENARIO 2: FALSE RECOVERY PREVENTION (FAILED != LOST)
    # -------------------------------------------------------------------------
    print("=" * 80)
    print(" SCENARIO 2: FALSE RECOVERY PREVENTION (FAILED != LOST)")
    print(" Failed -> Late Auth Flip -> ALREADY_RECOVERED -> Agent BLOCKED (No Action)")
    print("=" * 80)
    pay2 = PaymentRecord(
        payment_id="pay_demo_002",
        order_id="order_demo_002",
        amount=7499.0,
        method="upi",
        customer_segment="returning",
    )
    events2 = [
        Event(event="payment.created", payment_id="pay_demo_002", order_id="order_demo_002", ts="2026-08-10T11:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_002", order_id="order_demo_002", error_code="BANK_DOWNTIME", hardness="soft", ts="2026-08-10T11:00:06Z"),
        Event(event="payment.authorized", payment_id="pay_demo_002", order_id="order_demo_002", ts="2026-08-10T11:05:00Z"),
        Event(event="payment.captured", payment_id="pay_demo_002", order_id="order_demo_002", ts="2026-08-10T11:05:08Z"),
    ]
    res2 = orchestrator.run_lifecycle(pay2, events2)
    print_agent_decision_card(res2)

    # -------------------------------------------------------------------------
    # SCENARIO 3: ECONOMICALLY IRRATIONAL RECOVERY (NEGATIVE ENV)
    # -------------------------------------------------------------------------
    print("=" * 80)
    print(" SCENARIO 3: ECONOMICALLY IRRATIONAL RECOVERY (NEGATIVE ENV)")
    print(" VERIFIED_LOST -> Expected Net Value <= 0 -> Agent STOP -> Firewall FIREWALL-002")
    print("=" * 80)
    pay3 = PaymentRecord(
        payment_id="pay_demo_003",
        order_id="order_demo_003",
        amount=50.0,
        method="card",
        customer_segment="new",
    )
    events3 = [
        Event(event="payment.created", payment_id="pay_demo_003", order_id="order_demo_003", ts="2026-08-10T12:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_003", order_id="order_demo_003", error_code="USER_CANCELLED", hardness="hard", ts="2026-08-10T12:00:05Z"),
    ]
    res3 = orchestrator.run_lifecycle(pay3, events3)
    print_agent_decision_card(res3)

    # -------------------------------------------------------------------------
    # SCENARIO 4: HARD FAILURE SAFETY RULE (FIREWALL BLOCKS UNSAFE RETRY)
    # -------------------------------------------------------------------------
    print("=" * 80)
    print(" SCENARIO 4: HARD FAILURE SAFETY RULE")
    print(" Hard Failure (CARD_BLOCKED) -> Agent/User proposes RETRY -> Firewall Blocks FIREWALL-004")
    print("=" * 80)
    pay4 = PaymentRecord(
        payment_id="pay_demo_004",
        order_id="order_demo_004",
        amount=12000.0,
        method="card",
        customer_segment="returning",
    )
    events4 = [
        Event(event="payment.created", payment_id="pay_demo_004", order_id="order_demo_004", ts="2026-08-10T13:00:00Z"),
        Event(event="payment.failed", payment_id="pay_demo_004", order_id="order_demo_004", error_code="CARD_BLOCKED", hardness="hard", ts="2026-08-10T13:00:05Z"),
    ]
    res4 = orchestrator.run_lifecycle(pay4, events4, override_action=RecoveryAction.RETRY)
    print_agent_decision_card(res4)


if __name__ == "__main__":
    run_demo()
