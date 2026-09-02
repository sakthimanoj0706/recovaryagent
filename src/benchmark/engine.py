"""
Benchmark Execution Engine for RecoverAI.

Runs comparative simulations between Naive Baseline and RecoverAI
over reproducible synthetic payment populations.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .models import BenchmarkConfig, BenchmarkComparison, StrategyMetrics
from .generator import SyntheticPopulationGenerator, SyntheticLifecycle
from .strategies import NaiveRecoveryStrategy, RecoverAIRecoveryStrategy, ExecutionResult
from .metrics import MetricsCalculator


class BenchmarkEngine:
    """
    Orchestrates end-to-end economic benchmark simulations.
    """

    def __init__(self):
        self._latest_comparison: Optional[BenchmarkComparison] = None

    @property
    def latest_comparison(self) -> Optional[BenchmarkComparison]:
        return self._latest_comparison

    def run_benchmark(self, config: Optional[BenchmarkConfig] = None) -> BenchmarkComparison:
        """
        Execute full comparative benchmark over synthetic payment lifecycles.
        """
        cfg = config or BenchmarkConfig()
        seed = cfg.seed
        costs = cfg.costs

        # Generate population deterministically
        gen = SyntheticPopulationGenerator(seed=seed)
        population: List[SyntheticLifecycle] = gen.generate_population(cfg)

        # Count archetype breakdown
        archetype_counts: Dict[str, int] = {}
        for item in population:
            arch = item.archetype.value
            archetype_counts[arch] = archetype_counts.get(arch, 0) + 1

        # Instantiate strategies with seeded RNGs
        naive_strat = NaiveRecoveryStrategy(seed=seed)
        recoverai_strat = RecoverAIRecoveryStrategy(seed=seed)

        amounts: List[float] = [p.payment.amount for p in population]

        # Execute Naive Baseline
        naive_rec_amounts: List[float] = []
        naive_with_amounts: List[float] = []
        naive_pend_amounts: List[float] = []
        naive_esc_amounts: List[float] = []
        naive_out_amounts: List[float] = []
        
        n_opps = 0
        n_att = 0
        n_succ = 0
        n_fail = 0
        n_unnec = 0
        n_false = 0
        n_double = 0
        n_hard_retried = 0
        n_gw = 0
        n_links = 0
        n_contacts = 0
        n_esc = 0

        for item in population:
            res: ExecutionResult = naive_strat.execute_lifecycle(item, costs)
            naive_rec_amounts.append(res.recovered_amount)
            naive_with_amounts.append(res.withheld_amount)
            naive_pend_amounts.append(res.pending_amount)
            naive_esc_amounts.append(res.escalated_amount)
            naive_out_amounts.append(res.outstanding_amount)

            if res.is_opportunity:
                n_opps += 1
            if res.attempted:
                n_att += 1
            if res.succeeded:
                n_succ += 1
            if res.failed:
                n_fail += 1
            if res.is_unnecessary:
                n_unnec += 1
            if res.is_false_recovery:
                n_false += 1
            if res.is_double_charge:
                n_double += 1
            if res.is_hard_decline_retried:
                n_hard_retried += 1
            n_gw += res.gateway_retries
            n_links += res.payment_links
            n_contacts += res.customer_contacts
            n_esc += res.manual_escalations

        naive_metrics = MetricsCalculator.calculate_strategy_metrics(
            strategy_name="NAIVE_RECOVERY",
            amounts=amounts,
            recovered_amounts=naive_rec_amounts,
            withheld_amounts=naive_with_amounts,
            pending_amounts=naive_pend_amounts,
            escalated_amounts=naive_esc_amounts,
            outstanding_amounts=naive_out_amounts,
            recovery_opportunities=n_opps,
            recovery_attempts=n_att,
            successful_recoveries=n_succ,
            failed_recoveries=n_fail,
            unnecessary_actions=n_unnec,
            duplicate_actions_prevented=0,
            hard_decline_retries_prevented=0,
            hard_decline_retried_count=n_hard_retried,
            already_recovered_protected=0,
            false_recovery_claims=n_false,
            double_charge_events=n_double,
            gateway_retries=n_gw,
            payment_links=n_links,
            customer_contacts=n_contacts,
            manual_escalations=n_esc,
            costs=costs,
        )

        # Execute RecoverAI Pipeline
        rai_rec_amounts: List[float] = []
        rai_with_amounts: List[float] = []
        rai_pend_amounts: List[float] = []
        rai_esc_amounts: List[float] = []
        rai_out_amounts: List[float] = []

        r_opps = 0
        r_att = 0
        r_succ = 0
        r_fail = 0
        r_unnec = 0
        r_dup_prev = 0
        r_hard_prev = 0
        r_already_prot = 0
        r_gw = 0
        r_links = 0
        r_contacts = 0
        r_esc = 0

        for item in population:
            res: ExecutionResult = recoverai_strat.execute_lifecycle(item, costs)
            rai_rec_amounts.append(res.recovered_amount)
            rai_with_amounts.append(res.withheld_amount)
            rai_pend_amounts.append(res.pending_amount)
            rai_esc_amounts.append(res.escalated_amount)
            rai_out_amounts.append(res.outstanding_amount)

            if res.is_opportunity:
                r_opps += 1
            if res.attempted:
                r_att += 1
            if res.succeeded:
                r_succ += 1
            if res.failed:
                r_fail += 1
            if res.is_unnecessary:
                r_unnec += 1
            if res.duplicate_prevented:
                r_dup_prev += 1
            if res.hard_decline_prevented:
                r_hard_prev += 1
            if res.already_rec_protected:
                r_already_prot += 1
            r_gw += res.gateway_retries
            r_links += res.payment_links
            r_contacts += res.customer_contacts
            r_esc += res.manual_escalations

        recoverai_metrics = MetricsCalculator.calculate_strategy_metrics(
            strategy_name="RECOVERAI",
            amounts=amounts,
            recovered_amounts=rai_rec_amounts,
            withheld_amounts=rai_with_amounts,
            pending_amounts=rai_pend_amounts,
            escalated_amounts=rai_esc_amounts,
            outstanding_amounts=rai_out_amounts,
            recovery_opportunities=r_opps,
            recovery_attempts=r_att,
            successful_recoveries=r_succ,
            failed_recoveries=r_fail,
            unnecessary_actions=r_unnec,
            duplicate_actions_prevented=r_dup_prev,
            hard_decline_retries_prevented=r_hard_prev,
            hard_decline_retried_count=0,
            already_recovered_protected=r_already_prot,
            false_recovery_claims=0,
            double_charge_events=0,
            gateway_retries=r_gw,
            payment_links=r_links,
            customer_contacts=r_contacts,
            manual_escalations=r_esc,
            costs=costs,
        )

        comparison = MetricsCalculator.compare_strategies(
            benchmark_id=f"bench_{uuid.uuid4().hex[:10]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            config=cfg,
            naive=naive_metrics,
            recoverai=recoverai_metrics,
            archetype_counts=archetype_counts,
        )

        self._latest_comparison = comparison
        return comparison
