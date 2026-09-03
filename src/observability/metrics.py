"""
Step 20 — Production Latency Metrics Recorder.

Thread-safe in-memory latency store with p50/p95/p99 computation.
"""

import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Optional

from .models import LatencyMetrics


class LatencyRecorder:
    """Thread-safe in-memory latency store. Never raises on metrics failure."""

    MINIMUM_SAMPLES = 5

    def __init__(self):
        self._lock = threading.Lock()
        self._samples: Dict[str, List[float]] = {}

    def record(self, operation: str, latency_ms: float) -> None:
        """Record a latency sample for the given operation."""
        try:
            with self._lock:
                if operation not in self._samples:
                    self._samples[operation] = []
                self._samples[operation].append(latency_ms)
        except Exception:
            pass  # Metrics failure must never affect financial lifecycle

    @contextmanager
    def measure(self, operation: str):
        """Context manager to auto-measure and record latency."""
        start = time.perf_counter()
        try:
            yield
        finally:
            latency_ms = (time.perf_counter() - start) * 1000
            self.record(operation, latency_ms)

    def get_metrics(self, operation: str) -> LatencyMetrics:
        """Compute p50/p95/p99 for the given operation."""
        try:
            with self._lock:
                samples = list(self._samples.get(operation, []))

            if len(samples) < self.MINIMUM_SAMPLES:
                return LatencyMetrics(
                    operation=operation,
                    sample_count=len(samples),
                    status="INSUFFICIENT_DATA",
                )

            try:
                import numpy as np
                arr = np.array(samples)
                return LatencyMetrics(
                    operation=operation,
                    sample_count=len(samples),
                    p50_ms=round(float(np.percentile(arr, 50)), 2),
                    p95_ms=round(float(np.percentile(arr, 95)), 2),
                    p99_ms=round(float(np.percentile(arr, 99)), 2),
                    min_ms=round(float(arr.min()), 2),
                    max_ms=round(float(arr.max()), 2),
                    mean_ms=round(float(arr.mean()), 2),
                    status="OK",
                )
            except ImportError:
                # Numpy unavailable — use stdlib statistics
                import statistics
                sorted_s = sorted(samples)
                n = len(sorted_s)
                p50 = sorted_s[int(n * 0.50)]
                p95 = sorted_s[int(n * 0.95)]
                p99 = sorted_s[min(int(n * 0.99), n - 1)]
                return LatencyMetrics(
                    operation=operation,
                    sample_count=n,
                    p50_ms=round(p50, 2),
                    p95_ms=round(p95, 2),
                    p99_ms=round(p99, 2),
                    min_ms=round(min(sorted_s), 2),
                    max_ms=round(max(sorted_s), 2),
                    mean_ms=round(statistics.mean(sorted_s), 2),
                    status="OK",
                )
        except Exception:
            return LatencyMetrics(operation=operation, sample_count=0, status="INSUFFICIENT_DATA")

    def get_all_metrics(self) -> Dict[str, LatencyMetrics]:
        """Return metrics for all recorded operations."""
        try:
            with self._lock:
                ops = list(self._samples.keys())
            return {op: self.get_metrics(op) for op in ops}
        except Exception:
            return {}

    def get_sample_count(self, operation: str) -> int:
        """Return number of samples recorded for the given operation."""
        with self._lock:
            return len(self._samples.get(operation, []))

    def clear(self) -> None:
        """Clear all samples. Used for testing only."""
        with self._lock:
            self._samples.clear()


# Global singleton recorder — safe to import anywhere
_recorder = LatencyRecorder()


def get_recorder() -> LatencyRecorder:
    """Return the global latency recorder singleton."""
    return _recorder
