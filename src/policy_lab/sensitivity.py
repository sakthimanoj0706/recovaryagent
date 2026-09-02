"""
Sensitivity & Break-Even Analysis Engine for RecoverAI Policy Lab (Step 12).

Provides:
1. SensitivityAnalyzer: Multi-point parameter sweeps keeping population and other costs constant.
2. BreakEvenAnalyzer: Deterministic crossover point discovery.
"""

from typing import List, Dict, Any, Optional, Tuple
from .models import (
    EconomicEnvironment,
    CustomRecoveryPolicy,
    SensitivityRequest,
    SensitivityResult,
    SensitivityPoint,
    BreakEvenRequest,
    BreakEvenResult,
)
from .simulator import PolicyLabSimulator


class SensitivityAnalyzer:
    """
    Executes one-parameter sensitivity sweeps across controlled synthetic lifecycles.
    """

    DEFAULT_RANGES: Dict[str, List[float]] = {
        "retry_cost": [0.5, 1.0, 2.0, 5.0, 10.0, 25.0],
        "customer_contact_cost": [0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        "payment_link_cost": [0.5, 1.5, 3.0, 5.0, 10.0, 20.0],
        "chargeback_cost": [50.0, 100.0, 250.0, 500.0, 1000.0, 2500.0],
        "scheme_penalty": [0.0, 15.0, 50.0, 100.0, 250.0, 500.0],
        "recovery_probability_multiplier": [0.5, 0.75, 1.0, 1.25, 1.5, 2.0],
        "max_retries": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
    }

    @classmethod
    def run_sensitivity(cls, req: SensitivityRequest) -> SensitivityResult:
        param = req.parameter_name
        values: List[float] = []

        if req.parameter_values:
            values = req.parameter_values
        elif req.min_value is not None and req.max_value is not None:
            step_size = (req.max_value - req.min_value) / max(1, req.steps - 1)
            values = [req.min_value + (i * step_size) for i in range(req.steps)]
        elif param in cls.DEFAULT_RANGES:
            values = cls.DEFAULT_RANGES[param]
        else:
            values = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]

        points: List[SensitivityPoint] = []
        base_env = req.env
        policy = req.custom_policy

        for val in values:
            env_dict = base_env.model_dump()
            if param == "max_retries":
                env_dict[param] = int(val)
            else:
                env_dict[param] = float(val)

            cloned_env = EconomicEnvironment(**env_dict)
            sim_result = PolicyLabSimulator.run_simulation(env=cloned_env, custom_policy=policy)
            comp = sim_result.comparison
            n = comp.naive
            r = comp.recoverai
            c = comp.custom

            pt = SensitivityPoint(
                parameter_value=round(val, 4),
                naive_net_value=round(n.net_legitimate_value, 2),
                recoverai_net_value=round(r.net_legitimate_value, 2),
                custom_net_value=round(c.net_legitimate_value, 2),
                recoverai_lift_percent=round(comp.deltas.get("recoverai_net_lift_pct", 0.0), 2),
                custom_lift_percent=round(comp.deltas.get("custom_net_lift_pct", 0.0), 2),
                naive_safety_violations=n.false_recovery_claims + n.double_charge_events + n.hard_decline_retried_count,
                recoverai_safety_violations=r.false_recovery_claims + r.double_charge_events + r.hard_decline_retried_count,
                custom_safety_violations=c.false_recovery_claims + c.double_charge_events + c.hard_decline_retried_count,
                naive_unnecessary_actions=n.unnecessary_actions,
                recoverai_unnecessary_actions=r.unnecessary_actions,
                custom_unnecessary_actions=c.unnecessary_actions,
            )
            points.append(pt)

        summary = (
            f"Sensitivity analysis completed across {len(points)} evaluation points for parameter '{param}'. "
            f"Evaluated with population size {base_env.payment_population:,} (Seed: {base_env.random_seed})."
        )

        return SensitivityResult(
            parameter_name=param,
            points=points,
            summary=summary,
        )


class BreakEvenAnalyzer:
    """
    Discovers deterministic economic break-even crossover points.
    """

    @classmethod
    def find_break_even(cls, req: BreakEvenRequest) -> BreakEvenResult:
        param = req.parameter_name
        s_min = req.search_min
        s_max = req.search_max
        steps = 12

        step_size = (s_max - s_min) / max(1, steps - 1)
        grid_values = [s_min + (i * step_size) for i in range(steps)]

        evaluations: List[Tuple[float, float, float]] = []  # (param_val, naive_net, rai_net)

        for val in grid_values:
            env_dict = req.env.model_dump()
            if param == "max_retries":
                env_dict[param] = int(val)
            else:
                env_dict[param] = float(val)

            cloned_env = EconomicEnvironment(**env_dict)
            sim_res = PolicyLabSimulator.run_simulation(env=cloned_env, custom_policy=req.custom_policy)
            n_net = sim_res.comparison.naive.net_legitimate_value
            r_net = sim_res.comparison.recoverai.net_legitimate_value
            evaluations.append((val, n_net, r_net))

        # Check for crossover where (r_net - n_net) changes sign
        for i in range(len(evaluations) - 1):
            val1, n1, r1 = evaluations[i]
            val2, n2, r2 = evaluations[i + 1]

            diff1 = r1 - n1
            diff2 = r2 - n2

            if (diff1 * diff2) <= 0:
                # Crossover detected: linear interpolation
                if abs(diff2 - diff1) > 1e-6:
                    t = diff1 / (diff1 - diff2)
                    crossover_val = val1 + t * (val2 - val1)
                else:
                    crossover_val = (val1 + val2) / 2.0

                # Evaluate exact crossover point
                env_cross = req.env.model_dump()
                if param == "max_retries":
                    env_cross[param] = int(crossover_val)
                else:
                    env_cross[param] = float(crossover_val)
                cross_res = PolicyLabSimulator.run_simulation(
                    env=EconomicEnvironment(**env_cross),
                    custom_policy=req.custom_policy,
                )
                exact_n = cross_res.comparison.naive.net_legitimate_value
                exact_r = cross_res.comparison.recoverai.net_legitimate_value

                return BreakEvenResult(
                    parameter_name=param,
                    break_even_found=True,
                    break_even_value=round(crossover_val, 2),
                    naive_value=round(exact_n, 2),
                    recoverai_value=round(exact_r, 2),
                    search_range=(s_min, s_max),
                    explanation=(
                        f"Break-even crossover identified at {param} = Rs. {crossover_val:,.2f}. "
                        f"At this parameter value, RecoverAI Net Value (Rs. {exact_r:,.2f}) equals Naive Net Value (Rs. {exact_n:,.2f})."
                    ),
                )

        # No crossover found
        first_diff = evaluations[0][2] - evaluations[0][1]
        if first_diff > 0:
            expl = (
                f"RecoverAI strictly outperforms Naive Baseline across the entire tested {param} range "
                f"[Rs. {s_min:,.2f}, Rs. {s_max:,.2f}]. No break-even crossover point exists within this domain."
            )
        else:
            expl = (
                f"No break-even point found within the tested {param} range [Rs. {s_min:,.2f}, Rs. {s_max:,.2f}]."
            )

        return BreakEvenResult(
            parameter_name=param,
            break_even_found=False,
            break_even_value=None,
            naive_value=round(evaluations[0][1], 2),
            recoverai_value=round(evaluations[0][2], 2),
            search_range=(s_min, s_max),
            explanation=expl,
        )
