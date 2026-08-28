import sys
import json
import time
from pathlib import Path
from collections import defaultdict

# Ensure src is in sys.path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from evaluate_engine import load_dataset, GROUND_TRUTH_MAPPING
from agent.orchestrator import RecoverAIOrchestrator
from agent.llm import get_default_llm_client
from recovery.model import RecoveryProbabilityModel
from audit.logger import AuditLogger
from execution.executor import ActionExecutor
from execution.simulator import SyntheticSimulationEngine
from state_engine.models import FinancialState

def run_evaluation():
    start_time = time.time()
    
    payments, events, df = load_dataset()
    
    audit_file = Path("logs/full_dataset_audit.jsonl")
    audit_file.parent.mkdir(exist_ok=True)
    if audit_file.exists():
        audit_file.unlink()

    model_path = Path("models") / "recovery_probability_model.joblib"
    model = RecoveryProbabilityModel.load(model_path) if model_path.exists() else None
    
    audit_logger = AuditLogger(audit_file)
    llm_client = get_default_llm_client()
    executor = ActionExecutor(simulator=SyntheticSimulationEngine(simulation_seed=42))
    
    orchestrator = RecoverAIOrchestrator(
        llm_client=llm_client,
        model=model,
        audit_logger=audit_logger,
        executor=executor
    )

    total_payments = 0
    total_amount = 0.0

    state_counts = defaultdict(int)
    state_amounts = defaultdict(float)
    state_mismatches = []
    
    verified_lost_count = 0
    recovery_worthwhile = 0
    do_not_recover = 0
    firewall_approved = 0
    firewall_blocked = 0
    firewall_rules_counts = defaultdict(int)
    
    simulated_success = 0
    simulated_failure = 0

    hero_recovered = 0.0
    hero_withheld = 0.0
    hero_pending = 0.0
    hero_escalated = 0.0

    unnecessary_actions_avoided = 0
    processing_errors = []
    
    attempts_dispatched = 0
    successful_recoveries = 0

    events_by_pay = defaultdict(list)
    events_by_order = defaultdict(list)
    for e in events:
        if e.payment_id:
            events_by_pay[e.payment_id].append(e)
        if e.order_id:
            events_by_order[e.order_id].append(e)

    for payment in payments:
        try:
            total_payments += 1
            amt = payment.amount if payment.amount else 0.0
            total_amount += amt

            pay_events = events_by_pay.get(payment.payment_id, [])
            order_events = events_by_order.get(payment.order_id, []) if payment.order_id else []
            
            outcome = orchestrator.process_payment(payment, pay_events, order_events=order_events)

            pred_state = outcome.initial_state
            state_counts[pred_state] += 1
            state_amounts[pred_state] += amt

            expected_state = GROUND_TRUTH_MAPPING.get(payment.ground_truth_state)
            if expected_state and expected_state.value != pred_state:
                state_mismatches.append(f"Payment {payment.payment_id}: expected {expected_state.value}, got {pred_state}")

            if expected_state and expected_state.value == "ALREADY_RECOVERED" and pred_state == "ALREADY_RECOVERED":
                unnecessary_actions_avoided += 1

            if pred_state == "VERIFIED_LOST":
                verified_lost_count += 1
                env = outcome.expected_net_value or 0.0
                
                if env > 0:
                    recovery_worthwhile += 1
                    
                    if outcome.firewall_decision == "APPROVED":
                        firewall_approved += 1
                        attempts_dispatched += 1
                        
                        if outcome.execution_status == "SIMULATED_SUCCESS":
                            simulated_success += 1
                        elif outcome.execution_status == "SIMULATED_FAILURE":
                            simulated_failure += 1
                    else:
                        firewall_blocked += 1
                else:
                    do_not_recover += 1
                    
            if outcome.firewall_decision in ["BLOCKED", "STOP"] and outcome.firewall_rule:
                firewall_rules_counts[outcome.firewall_rule] += 1

            hero_recovered += outcome.amount_recovered
            hero_withheld += outcome.amount_withheld
            hero_pending += outcome.amount_pending
            hero_escalated += outcome.amount_escalated

            if outcome.final_outcome == "RECOVERY_SUCCESS":
                successful_recoveries += 1

        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            processing_errors.append((payment.payment_id, err_msg))

    exec_time = time.time() - start_time
    
    checksum_total = hero_recovered + hero_withheld + hero_pending + hero_escalated
    is_balanced = abs(checksum_total - total_amount) < 0.01

    report = []
    report.append("====================================================")
    report.append(" RECOVERAI FULL DATASET EVALUATION REPORT")
    report.append("====================================================")
    
    if not is_balanced:
        report.append("\n**WARNING**: BUG DETECTED - CHECKSUM DOES NOT BALANCE!")
        report.append(f"Total processed: Rs. {total_amount:,.2f}")
        report.append(f"Sum of 4 buckets: Rs. {checksum_total:,.2f}")
        report.append(f"Discrepancy: Rs. {total_amount - checksum_total:,.2f} missing from accounting.")
    else:
        report.append("\n**SUCCESS**: Checksum balances perfectly.")
        
    if processing_errors:
        report.append(f"\n**ERROR**: {len(processing_errors)} payments failed to process.")

    report.append("\n====================================================")
    report.append(" A. VOLUME")
    report.append("====================================================")
    report.append(f"Total payments processed: {total_payments}")
    report.append(f"Total amount processed  : Rs. {total_amount:,.2f}")

    report.append("\n====================================================")
    report.append(" B. FINANCIAL STATE ENGINE BREAKDOWN")
    report.append("====================================================")
    for state in ["ALREADY_RECOVERED", "VERIFIED_LOST", "UNCERTAIN", "EXCEPTION"]:
        report.append(f"{state:<20}: {state_counts[state]:>4} (Rs. {state_amounts[state]:,.2f})")
    
    if state_mismatches:
        report.append("\nMISMATCHES FOUND BETWEEN ENGINE CLASSIFICATION AND GROUND TRUTH:")
        for m in state_mismatches:
            report.append(" - " + m)
    else:
        report.append("\nGround truth cross-check passed: 0 mismatches.")

    report.append("\n====================================================")
    report.append(" C. RECOVERY PIPELINE FUNNEL (VERIFIED_LOST)")
    report.append("====================================================")
    report.append(f"VERIFIED_LOST entered intelligence: {verified_lost_count}")
    report.append(f"Scored RECOVERY_WORTHWHILE (+EV)  : {recovery_worthwhile}")
    report.append(f"Scored DO_NOT_RECOVER (-EV)       : {do_not_recover}")
    report.append(f"Of RECOVERY_WORTHWHILE:")
    report.append(f"  -> APPROVED by Firewall         : {firewall_approved}")
    report.append(f"  -> BLOCKED by Firewall          : {firewall_blocked}")
    report.append(f"Of APPROVED execution:")
    report.append(f"  -> SIMULATED_SUCCESS            : {simulated_success}")
    report.append(f"  -> SIMULATED_FAILURE            : {simulated_failure}")

    report.append("\n====================================================")
    report.append(" D. THE FOUR HERO ACCOUNTING BUCKETS")
    report.append("====================================================")
    report.append(f"Rs. ACTUALLY RECOVERED : Rs. {hero_recovered:,.2f}")
    report.append(f"Rs. CORRECTLY WITHHELD : Rs. {hero_withheld:,.2f}")
    report.append(f"Rs. PENDING / WAITING  : Rs. {hero_pending:,.2f}")
    report.append(f"Rs. ESCALATED          : Rs. {hero_escalated:,.2f}")
    report.append("----------------------------------------------------")
    report.append(f"Checksum Total         : Rs. {checksum_total:,.2f}")
    report.append(f"Total Amount Processed : Rs. {total_amount:,.2f}")
    report.append(f"Difference             : Rs. {total_amount - checksum_total:,.2f}")

    report.append("\n====================================================")
    report.append(" E. FIREWALL RULE FREQUENCY TABLE")
    report.append("====================================================")
    if firewall_rules_counts:
        sorted_rules = sorted(firewall_rules_counts.items(), key=lambda x: x[1], reverse=True)
        for rule_id, count in sorted_rules:
            report.append(f"{rule_id:<15}: {count} blocks")
    else:
        report.append("No firewall blocks recorded.")

    report.append("\n====================================================")
    report.append(" F. RECOVERY EFFECTIVENESS")
    report.append("====================================================")
    report.append(f"Recovery attempts dispatched : {attempts_dispatched}")
    if attempts_dispatched > 0:
        rr = (successful_recoveries / attempts_dispatched) * 100.0
        report.append(f"Successful recoveries        : {successful_recoveries}")
        report.append(f"Real recovery rate           : {rr:.2f}%")
    else:
        report.append("Real recovery rate           : N/A")

    report.append("\n====================================================")
    report.append(" G. UNNECESSARY ACTIONS AVOIDED")
    report.append("====================================================")
    report.append(f"Naive retries avoided on ALREADY_RECOVERED: {unnecessary_actions_avoided}")

    report.append("\n====================================================")
    report.append(f" Execution Time: {exec_time:.2f} seconds")
    report.append("====================================================")
    
    if processing_errors:
        report.append("\n====================================================")
        report.append(" PROCESSING ERRORS TRACEBACKS (First 3)")
        report.append("====================================================")
        for pid, err in processing_errors[:3]:
            report.append(f"\n--- Payment ID: {pid} ---")
            report.append(err)

    final_report_str = "\n".join(report)
    print(final_report_str)
    
    report_file = Path("reports/full_dataset_evaluation_report.md")
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(final_report_str, encoding="utf-8")
    print(f"\nReport saved to {report_file}")

if __name__ == "__main__":
    run_evaluation()
