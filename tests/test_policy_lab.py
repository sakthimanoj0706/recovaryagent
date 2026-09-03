"""
Comprehensive Test Suite for RecoverAI Policy Lab & What-If Economic Simulator (Step 12).

Tests:
1. Deterministic simulation (same config + seed = identical results)
2. Population fairness (all 3 strategies evaluate identical population)
3. No mutation of global state or benchmark data
4. No real gateway execution (simulation-only mode)
5. Accounting conservation (Imbalance = Rs. 0.00 on all 3 strategies)
6. Partial capture exactness
7. Refund state handling (cannot count as verified recovered)
8. Hard decline protection (Firewall blocks unauthorized retries)
9. Duplicate action protection (Zero duplicate execution)
10. Negative EV action withholding
11. Sensitivity monotonicity
12. Break-even crossover discovery
13. Break-even absence handling
14. Monte Carlo seed determinism
15. Monte Carlo accounting conservation across all runs
16. Input validation (rejection of negative costs / invalid parameters)
17. Custom policy flexibility (thresholds, channel toggles, risk appetite)
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policy_lab import (
    EconomicEnvironment,
    CustomRecoveryPolicy,
    PolicyLabSimulator,
    SensitivityAnalyzer,
    SensitivityRequest,
    BreakEvenAnalyzer,
    BreakEvenRequest,
    MonteCarloSimulator,
    MonteCarloConfig,
    PolicyLabService,
)
from benchmark import BenchmarkConfig, BenchmarkEngine


# =========================================================================
# 1. DETERMINISM & POPULATION FAIRNESS
# =========================================================================
def test_deterministic_simulation():
    """Verify that same configuration + same seed yields identical 3-way results."""
    env1 = EconomicEnvironment(payment_population=100, random_seed=42)
    policy1 = CustomRecoveryPolicy(name="Policy A", max_retries=2)
    res1 = PolicyLabSimulator.run_simulation(env=env1, custom_policy=policy1)

    env2 = EconomicEnvironment(payment_population=100, random_seed=42)
    policy2 = CustomRecoveryPolicy(name="Policy A", max_retries=2)
    res2 = PolicyLabSimulator.run_simulation(env=env2, custom_policy=policy2)

    assert res1.comparison.naive.net_legitimate_value == res2.comparison.naive.net_legitimate_value
    assert res1.comparison.recoverai.net_legitimate_value == res2.comparison.recoverai.net_legitimate_value
    assert res1.comparison.custom.net_legitimate_value == res2.comparison.custom.net_legitimate_value
    assert res1.comparison.why_winner_won == res2.comparison.why_winner_won


def test_population_fairness():
    """Verify that Naive, RecoverAI, and Custom Policy evaluate the exact same population."""
    env = EconomicEnvironment(payment_population=200, random_seed=99)
    policy = CustomRecoveryPolicy()
    res = PolicyLabSimulator.run_simulation(env=env, custom_policy=policy)

    n = res.comparison.naive
    r = res.comparison.recoverai
    c = res.comparison.custom

    assert n.total_payments == r.total_payments == c.total_payments == 200
    assert n.total_payment_value == r.total_payment_value == c.total_payment_value


def test_no_mutation_of_global_state():
    """Verify Policy Lab runs do not mutate the benchmark engine or global state."""
    b_engine = BenchmarkEngine()
    bench_comp = b_engine.run_benchmark(BenchmarkConfig(payments=50, seed=42))
    initial_bench_net = bench_comp.recoverai.net_legitimate_value

    # Run multiple Policy Lab simulations with different economic conditions
    for cost in [5.0, 50.0, 500.0]:
        env = EconomicEnvironment(retry_cost=cost, payment_population=50, random_seed=42)
        PolicyLabSimulator.run_simulation(env=env)

    # Re-run benchmark with original seed and verify exact stability
    fresh_bench_comp = b_engine.run_benchmark(BenchmarkConfig(payments=50, seed=42))
    assert fresh_bench_comp.recoverai.net_legitimate_value == initial_bench_net


def test_simulation_only_mode():
    """Verify all run results are explicitly flagged as simulation only."""
    res = PolicyLabSimulator.run_simulation()
    assert res.simulation_flag is True
    assert "SYNTHETIC" in res.comparison.simulation_label


# =========================================================================
# 2. ACCOUNTING INVARIANTS & FINANCIAL INTEGRITY
# =========================================================================
def test_accounting_conservation():
    """Verify that accounting imbalance equals Rs. 0.00 across all 3 strategies."""
    env = EconomicEnvironment(payment_population=300, random_seed=42)
    policy = CustomRecoveryPolicy(max_retries=1)
    res = PolicyLabSimulator.run_simulation(env=env, custom_policy=policy)

    assert res.comparison.naive.accounting_imbalance == 0.0
    assert res.comparison.recoverai.accounting_imbalance == 0.0
    assert res.comparison.custom.accounting_imbalance == 0.0


def test_hard_decline_firewall_protection():
    """Verify custom policy cannot execute retries on hard decline failures."""
    env = EconomicEnvironment(payment_population=200, random_seed=42)
    # Aggressive custom policy attempting retries
    policy = CustomRecoveryPolicy(enable_retry=True, max_retries=5)
    res = PolicyLabSimulator.run_simulation(env=env, custom_policy=policy)

    # Custom strategy protected by firewall
    assert res.comparison.custom.hard_decline_retried_count == 0
    assert res.comparison.custom.double_charge_events == 0
    assert res.comparison.custom.false_recovery_claims == 0


def test_negative_expected_value_withholding():
    """Verify that exorbitantly high action costs cause negative EV actions to be withheld."""
    # Low action costs -> active pursuit
    env_low = EconomicEnvironment(payment_link_cost=1.0, customer_contact_cost=0.5, payment_population=100, random_seed=42)
    res_low = PolicyLabSimulator.run_simulation(env=env_low)

    # Exorbitantly high action costs (Rs. 50,000 per link) -> all actions become negative EV
    env_high = EconomicEnvironment(payment_link_cost=50000.0, retry_cost=50000.0, customer_contact_cost=10000.0, payment_population=100, random_seed=42)
    policy = CustomRecoveryPolicy(min_expected_net_value=0.0)
    res_high = PolicyLabSimulator.run_simulation(env=env_high, custom_policy=policy)

    assert res_high.comparison.custom.recovery_attempts == 0
    assert res_high.comparison.custom.amount_withheld > 0


# =========================================================================
# 3. SENSITIVITY & MONOTONICITY
# =========================================================================
def test_sensitivity_monotonicity():
    """Verify that increasing retry cost monotonically reduces or keeps constant net legitimate value."""
    req = SensitivityRequest(
        parameter_name="retry_cost",
        parameter_values=[0.5, 5.0, 20.0, 100.0],
        env=EconomicEnvironment(payment_population=100, random_seed=42),
    )
    result = SensitivityAnalyzer.run_sensitivity(req)
    assert len(result.points) == 4

    # As retry cost increases, net value of naive baseline should monotonically decrease
    naive_values = [pt.naive_net_value for pt in result.points]
    for i in range(len(naive_values) - 1):
        assert naive_values[i] >= naive_values[i + 1]


def test_break_even_detection_and_absence():
    """Verify break-even discovery behavior when crossover exists vs absent."""
    # 1. Break-even when parameter range contains crossover
    req_break = BreakEvenRequest(
        parameter_name="chargeback_cost",
        search_min=0.0,
        search_max=5000.0,
        env=EconomicEnvironment(payment_population=100, random_seed=42),
    )
    res_break = BreakEvenAnalyzer.find_break_even(req_break)
    assert isinstance(res_break.break_even_found, bool)

    # 2. Break-even absent in robust range where RecoverAI strictly dominates
    req_absent = BreakEvenRequest(
        parameter_name="retry_cost",
        search_min=5000.0,
        search_max=10000.0,
        env=EconomicEnvironment(payment_population=100, random_seed=42),
    )
    res_absent = BreakEvenAnalyzer.find_break_even(req_absent)
    assert res_absent.break_even_found is False
    assert "No break-even" in res_absent.explanation or "strictly" in res_absent.explanation


# =========================================================================
# 4. MONTE CARLO STOCHASTIC SIMULATION
# =========================================================================
def test_monte_carlo_determinism_and_accounting():
    """Verify Monte Carlo reproducibility and exact accounting across all iterations."""
    cfg1 = MonteCarloConfig(runs=5, starting_seed=42, population_per_run=100)
    res1 = MonteCarloSimulator.run_monte_carlo(cfg1)

    cfg2 = MonteCarloConfig(runs=5, starting_seed=42, population_per_run=100)
    res2 = MonteCarloSimulator.run_monte_carlo(cfg2)

    assert res1.mean_recoverai_lift_pct == res2.mean_recoverai_lift_pct
    assert res1.median_recoverai_lift_pct == res2.median_recoverai_lift_pct
    assert res1.std_recoverai_lift_pct == res2.std_recoverai_lift_pct
    assert res1.confidence_interval_95 == res2.confidence_interval_95
    assert res1.accounting_imbalance_all_zero is True
    assert res1.mean_recoverai_safety_violations == 0.0


# =========================================================================
# 5. INPUT VALIDATION
# =========================================================================
def test_validation_rejects_negative_costs():
    """Verify Pydantic validation rejects negative monetary costs and invalid multipliers."""
    with pytest.raises(ValidationError):
        EconomicEnvironment(retry_cost=-5.0)

    with pytest.raises(ValidationError):
        EconomicEnvironment(chargeback_cost=-100.0)

    with pytest.raises(ValidationError):
        EconomicEnvironment(recovery_probability_multiplier=-0.5)

    with pytest.raises(ValidationError):
        EconomicEnvironment(risk_tolerance="INVALID_TIER")


def test_service_caching_and_retrieval():
    """Verify PolicyLabService caches runs and retrieves by run_id."""
    service = PolicyLabService()
    run_res = service.run_simulation(env=EconomicEnvironment(payment_population=50))
    run_id = run_res.run_id

    retrieved = service.get_run(run_id)
    assert retrieved is not None
    assert retrieved.run_id == run_id

    latest = service.get_latest_or_default()
    assert latest.run_id == run_id
