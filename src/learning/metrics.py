from typing import List, Dict, Any
from .models import RecoveryOutcome, DecisionQualityScore

class LearningMetricsCalculator:
    
    @staticmethod
    def calculate_expected_vs_actual(outcomes: List[RecoveryOutcome]) -> Dict[str, Any]:
        if not outcomes:
            return {
                "expected_recovery": 0.0,
                "actual_recovery": 0.0,
                "expected_cost": 0.0,
                "actual_cost": 0.0,
                "expected_net_value": 0.0,
                "actual_net_value": 0.0,
                "recovery_rate": 0.0
            }
            
        exp_rec = sum(o.expected_recovery for o in outcomes)
        act_rec = sum(o.actual_recovered_value for o in outcomes)
        
        exp_cost = sum(o.expected_cost for o in outcomes)
        act_cost = sum(o.actual_cost for o in outcomes)
        
        exp_net = sum(o.expected_net_value for o in outcomes)
        act_net = sum(o.actual_net_value for o in outcomes)
        
        successes = sum(1 for o in outcomes if o.recovery_success)
        rate = successes / len(outcomes)
        
        return {
            "expected_recovery": exp_rec,
            "actual_recovery": act_rec,
            "expected_cost": exp_cost,
            "actual_cost": act_cost,
            "expected_net_value": exp_net,
            "actual_net_value": act_net,
            "recovery_rate": rate
        }

    @staticmethod
    def calculate_decision_quality(outcome: RecoveryOutcome) -> DecisionQualityScore:
        # Decision Quality = economic accuracy + recovery accuracy + cost accuracy + safety correctness + verification correctness
        
        # Economic Accuracy: How close was expected net value to actual?
        # Max score 1.0, drops as absolute error increases (normalized against expected)
        abs_err = abs(outcome.expected_net_value - outcome.actual_net_value)
        base = max(abs(outcome.expected_net_value), 1.0)
        eco_acc = max(0.0, 1.0 - (abs_err / base))
        
        # Recovery Accuracy: Was the boolean expectation (P > 0.5) matched by actual success?
        expected_success = outcome.expected_probability > 0.5
        rec_acc = 1.0 if expected_success == outcome.recovery_success else 0.0
        
        # Cost Accuracy
        cost_err = abs(outcome.expected_cost - outcome.actual_cost)
        base_cost = max(outcome.expected_cost, 1.0)
        cost_acc = max(0.0, 1.0 - (cost_err / base_cost))
        
        # Safety Correctness: 1.0 if no policy/firewall violation occurred
        safety_acc = 1.0 if "APPROVED" in outcome.firewall_result else 0.0
        if outcome.actual_recovered_value > 0 and not outcome.recovery_success:
             # Phantom or double charge safety violation
             safety_acc = 0.0
             
        # Verification Correctness: 1.0 if execution success aligns with verified ledger
        verif_acc = 1.0 if outcome.verification_result == "VERIFIED" else 0.0
        
        total = (eco_acc * 0.3) + (rec_acc * 0.2) + (cost_acc * 0.1) + (safety_acc * 0.3) + (verif_acc * 0.1)
        
        return DecisionQualityScore(
            economic_accuracy=eco_acc,
            recovery_accuracy=rec_acc,
            cost_accuracy=cost_acc,
            safety_correctness=safety_acc,
            verification_correctness=verif_acc,
            total_score=total
        )
