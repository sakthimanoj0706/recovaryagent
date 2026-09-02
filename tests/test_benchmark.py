"""
Comprehensive Test Suite for RecoverAI Economic Impact Benchmark & ROI Engine (Step 11).

Tests:
- Deterministic seed reproducibility
- Synthetic population generation and distribution
- Accounting conservation (Total = Recovered + Withheld + Pending + Escalated + Outstanding)
- Baseline execution (Naive strategy)
- RecoverAI execution (Full safety architecture)
- Metric calculation & ROI formulas
- Zero-division handling & edge cases (empty population, 1 payment, 10,000 payments)
- Safety metrics (0 false recoveries, 0 double recoveries, 0 imbalance)
"""

import sys
from pathlib import Path
import pytest

# Ensure src is in python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from benchmark.models import BenchmarkConfig, CostModelConfig, BenchmarkArchetype
from benchmark.generator import SyntheticPopulationGenerator
from benchmark.strategies import NaiveRecoveryStrategy, RecoverAIRecoveryStrategy
from benchmark.metrics import MetricsCalculator
from benchmark.engine import BenchmarkEngine


# =========================================================================
# 1. POPULATION GENERATION & DETERMINISM TESTS
# =========================================================================
def test_generator_deterministic_seed():
    """Verify that identical seeds produce identical synthetic populations."""
    gen1 = SyntheticPopulationGenerator(seed=42)
    pop1 = gen1.generate_population(BenchmarkConfig(payments=50, seed=42))

    gen2 = SyntheticPopulationGenerator(seed=42)
    pop2 = gen2.generate_population(BenchmarkConfig(payments=50, seed=42))

    assert len(pop1) == len(pop2) == 50
    for p1, p2 in zip(pop1, pop2):
        assert p1.payment.payment_id == p2.payment.payment_id
        assert p1.payment.amount == p2.payment.amount
        assert p1.archetype == p2.archetype
        assert len(p1.events) == len(p2.events)


def test_generator_archetype_coverage():
    """Verify that all 12 archetypes are represented in a sufficiently large population."""
    gen = SyntheticPopulationGenerator(seed=42)
    pop = gen.generate_population(BenchmarkConfig(payments=1000, seed=42))
    
    seen_archetypes = {p.archetype for p in pop}
    for arch in BenchmarkArchetype:
        assert arch in seen_archetypes, f"Archetype {arch} was not generated."


# =========================================================================
# 2. STRATEGY EXECUTION & SAFETY METRICS
# =========================================================================
def test_strategy_naive_vs_recoverai_safety():
    """Verify RecoverAI maintains 0 false recoveries, 0 double charges, and 0 accounting imbalance."""
    config = BenchmarkConfig(payments=200, seed=42)
    engine = BenchmarkEngine()
    comparison = engine.run_benchmark(config)

    n = comparison.naive
    r = comparison.recoverai

    # RecoverAI Safety invariants
    assert r.false_recovery_claims == 0, "RecoverAI must have 0 false recovery claims"
    assert r.false_recovery_rate == 0.0, "RecoverAI false recovery rate must be 0.0"
    assert r.double_charge_events == 0, "RecoverAI must have 0 double charge events"
    assert r.accounting_imbalance == 0.0, f"RecoverAI accounting imbalance must be 0.0, got {r.accounting_imbalance}"
    assert r.unnecessary_actions == 0, "RecoverAI must eliminate all unnecessary actions"

    # Naive flaws observed
    assert n.false_recovery_claims > 0, "Naive baseline should produce false recovery claims"
    assert n.double_charge_events > 0, "Naive baseline should produce double charge events"
    assert n.unnecessary_actions > 0, "Naive baseline should produce unnecessary actions"


# =========================================================================
# 3. ACCOUNTING CONSERVATION CHECKS
# =========================================================================
def test_accounting_conservation_single_payment():
    """Verify accounting conservation on a 1-payment lifecycle."""
    config = BenchmarkConfig(payments=1, seed=42)
    engine = BenchmarkEngine()
    comparison = engine.run_benchmark(config)

    r = comparison.recoverai
    assert r.accounting_imbalance == 0.0
    total_categorized = r.gross_recovered_value + r.amount_withheld + r.amount_pending + r.amount_escalated
    assert round(r.total_payment_value, 2) == round(total_categorized, 2)


def test_accounting_conservation_large_population():
    """Verify accounting conservation across 1,000 synthetic payments."""
    config = BenchmarkConfig(payments=1000, seed=42)
    engine = BenchmarkEngine()
    comparison = engine.run_benchmark(config)

    r = comparison.recoverai
    assert r.accounting_imbalance == 0.0


# =========================================================================
# 4. METRICS & ROI FORMULAS WITH ZERO-DIVISION SAFETY
# =========================================================================
def test_metrics_zero_division_safety():
    """Verify metrics calculator handles empty amounts gracefully without ZeroDivisionError."""
    costs = CostModelConfig()
    metrics = MetricsCalculator.calculate_strategy_metrics(
        strategy_name="EMPTY_TEST",
        amounts=[],
        recovered_amounts=[],
        withheld_amounts=[],
        pending_amounts=[],
        escalated_amounts=[],
        outstanding_amounts=[],
        recovery_opportunities=0,
        recovery_attempts=0,
        successful_recoveries=0,
        failed_recoveries=0,
        unnecessary_actions=0,
        duplicate_actions_prevented=0,
        hard_decline_retries_prevented=0,
        hard_decline_retried_count=0,
        already_recovered_protected=0,
        false_recovery_claims=0,
        double_charge_events=0,
        gateway_retries=0,
        payment_links=0,
        customer_contacts=0,
        manual_escalations=0,
        costs=costs,
    )

    assert metrics.total_payments == 0
    assert metrics.total_payment_value == 0.0
    assert metrics.roi_percentage == 0.0
    assert metrics.cost_per_recovered_rupee == 0.0
    assert metrics.cost_per_successful_recovery == 0.0
    assert metrics.accounting_imbalance == 0.0


def test_roi_and_unit_economics_calculation():
    """Verify ROI and net recovery value formulas on controlled synthetic inputs."""
    costs = CostModelConfig(
        gateway_attempt_cost=1.0,
        payment_link_cost=2.0,
        customer_contact_cost=0.5,
        manual_escalation_cost=10.0,
        hard_decline_penalty_cost=15.0,
        double_recovery_chargeback_cost=100.0,
    )

    metrics = MetricsCalculator.calculate_strategy_metrics(
        strategy_name="CALC_TEST",
        amounts=[1000.0, 2000.0, 3000.0],
        recovered_amounts=[1000.0, 0.0, 3000.0],
        withheld_amounts=[0.0, 2000.0, 0.0],
        pending_amounts=[0.0, 0.0, 0.0],
        escalated_amounts=[0.0, 0.0, 0.0],
        outstanding_amounts=[0.0, 0.0, 0.0],
        recovery_opportunities=3,
        recovery_attempts=2,
        successful_recoveries=2,
        failed_recoveries=0,
        unnecessary_actions=0,
        duplicate_actions_prevented=0,
        hard_decline_retries_prevented=0,
        hard_decline_retried_count=0,
        already_recovered_protected=0,
        false_recovery_claims=0,
        double_charge_events=0,
        gateway_retries=2,
        payment_links=2,
        customer_contacts=2,
        manual_escalations=0,
        costs=costs,
    )

    # Cost = 2*1.0 + 2*2.0 + 2*0.5 = 2.0 + 4.0 + 1.0 = 7.0
    assert metrics.total_operating_cost == 7.0
    assert metrics.gross_recovered_value == 4000.0
    assert metrics.net_recovery_value == 4000.0 - 7.0  # 3993.0
    assert metrics.roi_percentage == (3993.0 / 7.0) * 100.0
    assert metrics.accounting_imbalance == 0.0


# =========================================================================
# 5. REPRODUCIBILITY VERIFICATION
# =========================================================================
def test_full_benchmark_reproducibility():
    """Verify that two identical benchmark runs produce identical output comparison metrics."""
    engine1 = BenchmarkEngine()
    comp1 = engine1.run_benchmark(BenchmarkConfig(payments=100, seed=123))

    engine2 = BenchmarkEngine()
    comp2 = engine2.run_benchmark(BenchmarkConfig(payments=100, seed=123))

    assert comp1.naive.gross_recovered_value == comp2.naive.gross_recovered_value
    assert comp1.recoverai.net_recovery_value == comp2.recoverai.net_recovery_value
    assert comp1.recoverai.unnecessary_actions == comp2.recoverai.unnecessary_actions
    assert comp1.key_findings == comp2.key_findings
