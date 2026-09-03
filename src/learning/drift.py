from typing import List, Dict, Any
from .models import RecoveryOutcome, DriftSignal, DriftStatus

class DriftDetector:
    
    @staticmethod
    def detect_failure_distribution_drift(baseline: List[RecoveryOutcome], current: List[RecoveryOutcome]) -> DriftSignal:
        if not baseline or not current:
            return DriftSignal(metric="failure_distribution", baseline=0.0, current=0.0, delta=0.0, threshold=0.1, status=DriftStatus.INSUFFICIENT_DATA)
            
        def dist(outcomes):
            counts = {}
            for o in outcomes:
                counts[o.failure_class] = counts.get(o.failure_class, 0) + 1
            n = len(outcomes)
            return {k: v/n for k, v in counts.items()}
            
        b_dist = dist(baseline)
        c_dist = dist(current)
        
        # Simple total variation distance
        tvd = 0.0
        keys = set(b_dist.keys()).union(set(c_dist.keys()))
        for k in keys:
            tvd += abs(b_dist.get(k, 0.0) - c_dist.get(k, 0.0))
        tvd /= 2.0
        
        threshold = 0.15
        if tvd > threshold:
            status = DriftStatus.DRIFT_DETECTED
        elif tvd > threshold * 0.5:
            status = DriftStatus.WARNING
        else:
            status = DriftStatus.STABLE
            
        return DriftSignal(
            metric="failure_distribution_tvd",
            baseline=0.0,
            current=tvd,
            delta=tvd,
            threshold=threshold,
            status=status
        )

    @staticmethod
    def detect_success_rate_drift(baseline: List[RecoveryOutcome], current: List[RecoveryOutcome]) -> DriftSignal:
        if not baseline or not current:
            return DriftSignal(metric="success_rate", baseline=0.0, current=0.0, delta=0.0, threshold=0.05, status=DriftStatus.INSUFFICIENT_DATA)
            
        b_rate = sum(1 for o in baseline if o.recovery_success) / len(baseline)
        c_rate = sum(1 for o in current if o.recovery_success) / len(current)
        
        delta = abs(b_rate - c_rate)
        threshold = 0.05
        
        if delta > threshold:
            status = DriftStatus.DRIFT_DETECTED
        elif delta > threshold * 0.5:
            status = DriftStatus.WARNING
        else:
            status = DriftStatus.STABLE
            
        return DriftSignal(
            metric="success_rate",
            baseline=b_rate,
            current=c_rate,
            delta=delta,
            threshold=threshold,
            status=status
        )
