"""
Policy Lab Service Layer for RecoverAI (Step 12).

Provides singleton orchestration and run history caching for Policy Lab APIs.
"""

from typing import Dict, Optional
from .models import (
    EconomicEnvironment,
    CustomRecoveryPolicy,
    PolicyLabRunResult,
    SensitivityRequest,
    SensitivityResult,
    BreakEvenRequest,
    BreakEvenResult,
    MonteCarloConfig,
    MonteCarloResult,
)
from .simulator import PolicyLabSimulator
from .sensitivity import SensitivityAnalyzer, BreakEvenAnalyzer
from .monte_carlo import MonteCarloSimulator


class PolicyLabService:
    """
    Singleton service managing Policy Lab simulations, sensitivity sweeps, and Monte Carlo runs.
    """

    def __init__(self):
        self._runs: Dict[str, PolicyLabRunResult] = {}
        self._latest_run: Optional[PolicyLabRunResult] = None

    @property
    def latest_run(self) -> Optional[PolicyLabRunResult]:
        return self._latest_run

    def run_simulation(
        self,
        env: Optional[EconomicEnvironment] = None,
        custom_policy: Optional[CustomRecoveryPolicy] = None,
    ) -> PolicyLabRunResult:
        """Execute a 3-way comparative simulation and cache the result."""
        result = PolicyLabSimulator.run_simulation(env=env, custom_policy=custom_policy)
        self._runs[result.run_id] = result
        self._latest_run = result
        return result

    def get_run(self, run_id: str) -> Optional[PolicyLabRunResult]:
        """Retrieve a cached simulation run by its unique run_id."""
        return self._runs.get(run_id)

    def get_latest_or_default(self) -> PolicyLabRunResult:
        """Get the latest run, or execute a fast 1,000-payment default simulation if none exists."""
        if self._latest_run is None:
            return self.run_simulation()
        return self._latest_run

    def run_sensitivity(self, req: SensitivityRequest) -> SensitivityResult:
        """Execute a one-parameter sensitivity analysis sweep."""
        return SensitivityAnalyzer.run_sensitivity(req)

    def find_break_even(self, req: BreakEvenRequest) -> BreakEvenResult:
        """Execute deterministic break-even discovery."""
        return BreakEvenAnalyzer.find_break_even(req)

    def run_monte_carlo(self, config: MonteCarloConfig) -> MonteCarloResult:
        """Execute multi-seed Monte Carlo simulation."""
        return MonteCarloSimulator.run_monte_carlo(config)
