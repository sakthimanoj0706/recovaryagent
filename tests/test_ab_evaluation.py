import pytest
from experiment.models import ABTestConfig, CounterfactualValueProof, StrategyResult
from experiment.ab_engine import AutonomousABExperimentEngine


def test_ab_evaluation_deterministic_proof():
    # Arrange
    config = ABTestConfig(population_size=100, random_seed=42)
    
    # Act
    proof = AutonomousABExperimentEngine.run_experiment(config)
    
    # Assert
    assert isinstance(proof, CounterfactualValueProof)
    assert proof.config.population_size == 100
    
    # The A/B delta should precisely match
    expected_incremental_net = proof.recoverai_result.net_legitimate_value - proof.baseline_result.net_legitimate_value
    assert proof.incremental_net_value == pytest.approx(expected_incremental_net, 0.01)
    
    # The safety violations prevented should exactly match
    expected_violations = proof.baseline_result.safety_violations - proof.recoverai_result.safety_violations
    assert proof.safety_violations_prevented == expected_violations
    
    # Check signature determinism
    sig1 = proof.proof_signature_sha256
    assert sig1 is not None
    assert len(sig1) == 64  # SHA-256 hex length
    
    # Running exactly the same config should produce exactly the same proof
    proof2 = AutonomousABExperimentEngine.run_experiment(config)
    assert proof2.proof_signature_sha256 == sig1


def test_ab_evaluation_isolates_value():
    """Verify that RecoverAI isolates value compared to Naive."""
    config = ABTestConfig(population_size=500, random_seed=99)
    proof = AutonomousABExperimentEngine.run_experiment(config)
    
    # RecoverAI should have higher net legitimate value due to avoiding penalties and bad retries
    assert proof.incremental_net_value > 0
    assert proof.safety_violations_prevented > 0
    
    # RecoverAI should have strictly 0 safety violations
    assert proof.recoverai_result.safety_violations == 0
    assert proof.recoverai_result.false_recovery_claims == 0
    assert proof.recoverai_result.double_charge_violations == 0
