from typing import List, Dict, Any
from .models import RecoveryOutcome
import math

class CalibrationMonitor:
    
    @staticmethod
    def calculate_calibration(outcomes: List[RecoveryOutcome]) -> List[Dict[str, Any]]:
        # 10 buckets: 0.0-0.1, 0.1-0.2, ...
        buckets = {i: {"count": 0, "expected_sum": 0.0, "actual_successes": 0} for i in range(10)}
        
        for o in outcomes:
            prob = max(0.0, min(0.999, o.expected_probability))
            b = int(prob * 10)
            buckets[b]["count"] += 1
            buckets[b]["expected_sum"] += prob
            if o.recovery_success:
                buckets[b]["actual_successes"] += 1
                
        results = []
        for i in range(10):
            cnt = buckets[i]["count"]
            exp_rate = buckets[i]["expected_sum"] / cnt if cnt > 0 else 0.0
            act_rate = buckets[i]["actual_successes"] / cnt if cnt > 0 else 0.0
            err = abs(exp_rate - act_rate) if cnt > 0 else 0.0
            
            results.append({
                "bucket": f"{i/10.0:.1f}-{i/10.0+0.1:.1f}",
                "count": cnt,
                "predicted_rate": exp_rate,
                "actual_rate": act_rate,
                "calibration_error": err
            })
            
        return results
