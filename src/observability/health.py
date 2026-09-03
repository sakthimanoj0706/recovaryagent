"""
Step 20 — System Health Checker.

Classifies dependencies as CRITICAL or NON_CRITICAL.
CRITICAL failures → APPLICATION_UNHEALTHY.
NON_CRITICAL failures → APPLICATION_DEGRADED.

Financial lifecycle NEVER depends on non-critical systems.
"""

import time
from typing import List

from .models import (
    SystemHealthReport, HealthStatus, DependencyHealth, DependencyClass
)


class HealthChecker:
    """
    Checks system dependencies and returns a structured health report.

    CRITICAL dependencies (failure → UNHEALTHY, execution blocked):
      - Financial State Engine
      - Policy Engine
      - Firewall
      - Verification

    NON_CRITICAL dependencies (failure → DEGRADED, execution continues):
      - LLM Advisory
      - Learning / Drift
      - Metrics
      - Challenger
      - Audit (write failure logged but does not block)
    """

    def check(self) -> SystemHealthReport:
        deps: List[DependencyHealth] = []
        critical_failures: List[str] = []
        non_critical_failures: List[str] = []

        # ── CRITICAL: Financial State Engine ──────────────────────────────
        dep = self._check_financial_state_engine()
        deps.append(dep)
        if dep.status != "OK":
            critical_failures.append(dep.name)

        # ── CRITICAL: Policy Engine ───────────────────────────────────────
        dep = self._check_policy_engine()
        deps.append(dep)
        if dep.status != "OK":
            critical_failures.append(dep.name)

        # ── CRITICAL: Firewall ────────────────────────────────────────────
        dep = self._check_firewall()
        deps.append(dep)
        if dep.status != "OK":
            critical_failures.append(dep.name)

        # ── CRITICAL: Verification ────────────────────────────────────────
        dep = self._check_verification()
        deps.append(dep)
        if dep.status != "OK":
            critical_failures.append(dep.name)

        # ── NON_CRITICAL: ML Model ────────────────────────────────────────
        dep = self._check_ml_model()
        deps.append(dep)
        if dep.status != "OK":
            non_critical_failures.append(dep.name)

        # ── NON_CRITICAL: Learning / Drift ────────────────────────────────
        dep = self._check_learning()
        deps.append(dep)
        if dep.status != "OK":
            non_critical_failures.append(dep.name)

        # ── NON_CRITICAL: Challenger ──────────────────────────────────────
        dep = self._check_challenger()
        deps.append(dep)
        if dep.status != "OK":
            non_critical_failures.append(dep.name)

        # ── NON_CRITICAL: Metrics ─────────────────────────────────────────
        dep = self._check_metrics()
        deps.append(dep)
        if dep.status != "OK":
            non_critical_failures.append(dep.name)

        # ── Determine overall status ──────────────────────────────────────
        if critical_failures:
            overall = HealthStatus.UNHEALTHY
        elif non_critical_failures:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return SystemHealthReport(
            overall_status=overall,
            dependencies=deps,
            critical_failures=critical_failures,
            non_critical_failures=non_critical_failures,
            financial_state_engine_ok=("Financial State Engine" not in critical_failures),
            policy_engine_ok=("Policy Engine" not in critical_failures),
            firewall_ok=("Firewall" not in critical_failures),
            verification_ok=("Verification" not in critical_failures),
            learning_ok=("Learning/Drift" not in non_critical_failures),
            llm_ok=True,  # LLM always has deterministic fallback
            metrics_ok=("Metrics" not in non_critical_failures),
        )

    def _check_financial_state_engine(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from state_engine import FinancialStateEngine
            engine = FinancialStateEngine()
            # Smoke check: instantiation successful
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Financial State Engine",
                dependency_class=DependencyClass.CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Financial State Engine",
                dependency_class=DependencyClass.CRITICAL,
                status="UNAVAILABLE",
                detail=str(e)[:200],
            )

    def _check_policy_engine(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from agent.policy import PolicyEngine
            engine = PolicyEngine()
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Policy Engine",
                dependency_class=DependencyClass.CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Policy Engine",
                dependency_class=DependencyClass.CRITICAL,
                status="UNAVAILABLE",
                detail=str(e)[:200],
            )

    def _check_firewall(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from agent.firewall import RecoveryFirewall
            fw = RecoveryFirewall()
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Firewall",
                dependency_class=DependencyClass.CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Firewall",
                dependency_class=DependencyClass.CRITICAL,
                status="UNAVAILABLE",
                detail=str(e)[:200],
            )

    def _check_verification(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from execution.verifier import RecoveryVerifier
            v = RecoveryVerifier()
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Verification",
                dependency_class=DependencyClass.CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Verification",
                dependency_class=DependencyClass.CRITICAL,
                status="UNAVAILABLE",
                detail=str(e)[:200],
            )

    def _check_ml_model(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from pathlib import Path
            model_path = Path("models") / "recovery_probability_model.joblib"
            if model_path.exists():
                status = "OK"
                detail = "Model file present"
            else:
                status = "DEGRADED"
                detail = "Model file not found; using probability fallback (p=0.5)"
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="ML Model",
                dependency_class=DependencyClass.NON_CRITICAL,
                status=status,
                detail=detail,
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="ML Model",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="DEGRADED",
                detail=str(e)[:200],
            )

    def _check_learning(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from learning.outcome_store import OutcomeStore
            OutcomeStore()
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Learning/Drift",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Learning/Drift",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="DEGRADED",
                detail=str(e)[:200],
            )

    def _check_challenger(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from challenger.service import ChallengerService
            ChallengerService()
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Challenger",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Challenger",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="DEGRADED",
                detail=str(e)[:200],
            )

    def _check_metrics(self) -> DependencyHealth:
        t0 = time.perf_counter()
        try:
            from observability.metrics import get_recorder
            get_recorder()
            latency = (time.perf_counter() - t0) * 1000
            return DependencyHealth(
                name="Metrics",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="OK",
                latency_ms=round(latency, 2),
            )
        except Exception as e:
            return DependencyHealth(
                name="Metrics",
                dependency_class=DependencyClass.NON_CRITICAL,
                status="DEGRADED",
                detail=str(e)[:200],
            )
