from experiment.models import ABTestConfig
from experiment.ab_engine import AutonomousABExperimentEngine

def verify():
    # 1. Run with 1000 population, seed 42
    config1 = ABTestConfig(population_size=1000, random_seed=42)
    proof1 = AutonomousABExperimentEngine.run_experiment(config1)
    
    # 2. Run again with exactly the same config
    config2 = ABTestConfig(population_size=1000, random_seed=42)
    proof2 = AutonomousABExperimentEngine.run_experiment(config2)
    
    print(f"Proof 1 Hash: {proof1.proof_signature_sha256}")
    print(f"Proof 2 Hash: {proof2.proof_signature_sha256}")
    print(f"Match exactly? {proof1.proof_signature_sha256 == proof2.proof_signature_sha256}")
    
    # 3. Change one input (population size)
    config3 = ABTestConfig(population_size=1001, random_seed=42)
    proof3 = AutonomousABExperimentEngine.run_experiment(config3)
    print(f"Proof 3 Hash (changed pop): {proof3.proof_signature_sha256}")
    print(f"Changed hash? {proof1.proof_signature_sha256 != proof3.proof_signature_sha256}")

    # 4. Known Positive Lift Fixture (from test)
    pos_config = ABTestConfig(population_size=500, random_seed=99)
    pos_proof = AutonomousABExperimentEngine.run_experiment(pos_config)
    print(f"\nPositive Fixture - Naive: {pos_proof.baseline_result.net_legitimate_value}")
    print(f"Positive Fixture - RecoverAI: {pos_proof.recoverai_result.net_legitimate_value}")
    print(f"Positive Fixture - Lift: {pos_proof.incremental_net_value}")

    # 5. Neutral/Alternative Fixture (from test)
    neutral_config = ABTestConfig(
        population_size=100, 
        random_seed=123,
        gateway_attempt_cost=0.0,
        payment_link_cost=0.0,
        customer_contact_cost=0.0,
        manual_escalation_cost=0.0,
        hard_decline_penalty_cost=0.0,
        double_recovery_chargeback_cost=0.0
    )
    neu_proof = AutonomousABExperimentEngine.run_experiment(neutral_config)
    print(f"\nNeutral Fixture - Naive: {neu_proof.baseline_result.net_legitimate_value}")
    print(f"Neutral Fixture - RecoverAI: {neu_proof.recoverai_result.net_legitimate_value}")
    print(f"Neutral Fixture - Lift: {neu_proof.incremental_net_value}")

if __name__ == "__main__":
    verify()
