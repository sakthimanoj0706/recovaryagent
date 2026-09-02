import uuid
from datetime import datetime, timezone
from typing import Optional

from benchmark.engine import BenchmarkEngine
from benchmark.models import BenchmarkConfig, BenchmarkComparison, CostModelConfig

from .models import (
    ABTestConfig,
    StrategyResult,
    CounterfactualValueProof
)


class AutonomousABExperimentEngine:
    """
    Executes a formal Autonomous Recovery A/B Experiment and generates a cryptographically 
    verifiable Counterfactual Financial Value Proof (Step 15).
    """

    @classmethod
    def run_experiment(cls, config: Optional[ABTestConfig] = None) -> CounterfactualValueProof:
        """
        Execute the A/B evaluation and seal the results in a Proof.
        """
        cfg = config or ABTestConfig()

        # Map ABTestConfig to BenchmarkConfig
        costs = CostModelConfig(
            gateway_attempt_cost=cfg.gateway_attempt_cost,
            payment_link_cost=cfg.payment_link_cost,
            customer_contact_cost=cfg.customer_contact_cost,
            manual_escalation_cost=cfg.manual_escalation_cost,
            hard_decline_penalty_cost=cfg.hard_decline_penalty_cost,
            double_recovery_chargeback_cost=cfg.double_recovery_chargeback_cost
        )
        
        bench_cfg = BenchmarkConfig(
            payments=cfg.population_size,
            seed=cfg.random_seed,
            costs=costs
        )

        # Execute exact deterministc side-by-side comparison
        engine = BenchmarkEngine()
        comparison: BenchmarkComparison = engine.run_benchmark(bench_cfg)

        naive_res = comparison.naive
        ai_res = comparison.recoverai

        # Map to standard StrategyResult
        naive_strategy_result = StrategyResult(
            strategy_name="NAIVE_BASELINE",
            total_recovered=naive_res.gross_recovered_value,
            total_withheld=naive_res.amount_withheld,
            total_escalated=naive_res.amount_escalated,
            total_pending=naive_res.amount_pending,
            total_costs=naive_res.total_operating_cost,
            net_legitimate_value=naive_res.net_legitimate_value,
            false_recovery_claims=naive_res.false_recovery_claims,
            double_charge_violations=naive_res.double_charge_events,
            safety_violations=naive_res.false_recovery_claims + naive_res.double_charge_events + naive_res.hard_decline_retried_count
        )

        ai_strategy_result = StrategyResult(
            strategy_name="RECOVERAI",
            total_recovered=ai_res.gross_recovered_value,
            total_withheld=ai_res.amount_withheld,
            total_escalated=ai_res.amount_escalated,
            total_pending=ai_res.amount_pending,
            total_costs=ai_res.total_operating_cost,
            net_legitimate_value=ai_res.net_legitimate_value,
            false_recovery_claims=ai_res.false_recovery_claims,
            double_charge_violations=ai_res.double_charge_events,
            safety_violations=ai_res.false_recovery_claims + ai_res.double_charge_events + ai_res.hard_decline_retried_count
        )

        # Calculate isolated AI value metrics
        incremental_gross = ai_res.gross_recovered_value - naive_res.gross_recovered_value
        incremental_net = comparison.net_value_lift_amount
        cost_savings = naive_res.total_operating_cost - ai_res.total_operating_cost

        violations_prevented = (naive_res.false_recovery_claims + naive_res.double_charge_events + naive_res.hard_decline_retried_count) - \
                               (ai_res.false_recovery_claims + ai_res.double_charge_events + ai_res.hard_decline_retried_count)

        unnecessary_avoided = naive_res.unnecessary_actions - ai_res.unnecessary_actions

        # Generate the Counterfactual Proof Artifact
        proof = CounterfactualValueProof(
            config=cfg,
            baseline_result=naive_strategy_result,
            recoverai_result=ai_strategy_result,
            incremental_gross_recovery=incremental_gross,
            cost_savings=cost_savings,
            incremental_net_value=incremental_net,
            safety_violations_prevented=violations_prevented,
            unnecessary_actions_avoided=unnecessary_avoided,
        )

        # Seal with SHA-256
        proof.sign_proof()
        return proof
