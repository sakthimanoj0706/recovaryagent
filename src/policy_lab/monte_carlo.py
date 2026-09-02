"""
Monte Carlo Simulation Engine for RecoverAI Policy Lab (Step 12).

Simulates multiple independent synthetic populations across sequential pseudo-random seeds.
Aggregates mean/median value lift, variance, 95% confidence intervals, and verifies global accounting conservation.
"""

import math
from typing import List
from .models import MonteCarloConfig, MonteCarloResult, EconomicEnvironment
from .simulator import PolicyLabSimulator


class MonteCarloSimulator:
    """
    Executes multi-run stochastic Monte Carlo simulations over deterministic seed sequences.
    """

    @classmethod
    def run_monte_carlo(cls, config: MonteCarloConfig) -> MonteCarloResult:
        runs = config.runs
        start_seed = config.starting_seed
        pop_per_run = config.population_per_run
        base_env = config.env
        policy = config.custom_policy

        rai_lifts: List[float] = []
        custom_lifts: List[float] = []
        naive_violations: List[int] = []
        rai_violations: List[int] = []
        custom_violations: List[int] = []
        unnec_saved: List[int] = []
        all_imbalances_zero = True

        for i in range(runs):
            current_seed = start_seed + i
            env_dict = base_env.model_dump()
            env_dict["random_seed"] = current_seed
            env_dict["payment_population"] = pop_per_run
            run_env = EconomicEnvironment(**env_dict)

            sim_result = PolicyLabSimulator.run_simulation(env=run_env, custom_policy=policy)
            comp = sim_result.comparison

            n = comp.naive
            r = comp.recoverai
            c = comp.custom

            rai_lift = comp.deltas.get("recoverai_net_lift_pct", 0.0)
            c_lift = comp.deltas.get("custom_net_lift_pct", 0.0)

            rai_lifts.append(rai_lift)
            custom_lifts.append(c_lift)

            n_viol = n.false_recovery_claims + n.double_charge_events + n.hard_decline_retried_count
            r_viol = r.false_recovery_claims + r.double_charge_events + r.hard_decline_retried_count
            c_viol = c.false_recovery_claims + c.double_charge_events + c.hard_decline_retried_count

            naive_violations.append(n_viol)
            rai_violations.append(r_viol)
            custom_violations.append(c_viol)

            unnec_saved.append(n.unnecessary_actions - r.unnecessary_actions)

            if n.accounting_imbalance != 0.0 or r.accounting_imbalance != 0.0 or c.accounting_imbalance != 0.0:
                all_imbalances_zero = False

        # Calculate statistics
        mean_rai = sum(rai_lifts) / max(1, runs)
        sorted_rai = sorted(rai_lifts)
        median_rai = sorted_rai[len(sorted_rai) // 2] if sorted_rai else 0.0
        variance_rai = (sum((x - mean_rai) ** 2 for x in rai_lifts) / max(1, runs)) if runs > 0 else 0.0
        std_rai = math.sqrt(variance_rai)
        min_rai = min(rai_lifts) if rai_lifts else 0.0
        max_rai = max(rai_lifts) if rai_lifts else 0.0

        ci_half = (1.96 * (std_rai / math.sqrt(runs))) if runs > 1 else 0.0
        ci_95 = (round(max(0.0, mean_rai - ci_half), 2), round(mean_rai + ci_half, 2))

        mean_custom = sum(custom_lifts) / max(1, runs)
        sorted_custom = sorted(custom_lifts)
        median_custom = sorted_custom[len(sorted_custom) // 2] if sorted_custom else 0.0

        mean_n_viol = sum(naive_violations) / max(1, runs)
        mean_r_viol = sum(rai_violations) / max(1, runs)
        mean_c_viol = sum(custom_violations) / max(1, runs)
        mean_unnec_saved = sum(unnec_saved) / max(1, runs)

        return MonteCarloResult(
            total_runs=runs,
            starting_seed=start_seed,
            population_per_run=pop_per_run,
            mean_recoverai_lift_pct=round(mean_rai, 2),
            median_recoverai_lift_pct=round(median_rai, 2),
            std_recoverai_lift_pct=round(std_rai, 2),
            min_recoverai_lift_pct=round(min_rai, 2),
            max_recoverai_lift_pct=round(max_rai, 2),
            confidence_interval_95=ci_95,
            mean_custom_lift_pct=round(mean_custom, 2),
            median_custom_lift_pct=round(median_custom, 2),
            mean_naive_safety_violations=round(mean_n_viol, 1),
            mean_recoverai_safety_violations=round(mean_r_viol, 1),
            mean_custom_safety_violations=round(mean_c_viol, 1),
            mean_unnecessary_actions_saved=round(mean_unnec_saved, 1),
            accounting_imbalance_all_zero=all_imbalances_zero,
            disclaimer="Synthetic simulation. Not real-world production performance.",
        )
