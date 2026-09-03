"""
Step 20 — Observability Service.

Combines tracing, metrics, and health checking into a single service.
Thread-safe singleton. Never raises — degrades gracefully.
"""

import threading
import uuid
from typing import Optional, Any, List, Dict

from .models import (
    ObservabilityEvent, OperationType, OperationStatus,
    SystemHealthReport, DecisionTrace
)
from .metrics import LatencyRecorder, get_recorder
from .tracing import DecisionTracer
from .health import HealthChecker


class ObservabilityService:
    """
    Production observability service for RecoverAI.

    Safe to import from any module. All operations fail-safe:
    if observability fails, the financial lifecycle continues unaffected.
    """

    def __init__(self):
        self._recorder = get_recorder()
        self._health_checker = HealthChecker()
        self._events: List[ObservabilityEvent] = []
        self._lock = threading.Lock()

    def record_event(
        self,
        operation: OperationType,
        status: OperationStatus,
        correlation_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        decision_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        strategy_version: Optional[str] = None,
        latency_ms: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Optional[ObservabilityEvent]:
        """Record a structured observability event. Never raises."""
        try:
            cid = correlation_id or f"corr_{uuid.uuid4().hex[:12]}"
            event = ObservabilityEvent(
                correlation_id=cid,
                request_id=request_id,
                payment_id=payment_id,
                decision_id=decision_id,
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                operation=operation,
                status=status,
                latency_ms=latency_ms,
                details=details or {},
                error=error,
            )
            if latency_ms is not None:
                self._recorder.record(operation.value if hasattr(operation, 'value') else str(operation), latency_ms)
            with self._lock:
                self._events.append(event)
                # Keep last 10,000 events in memory
                if len(self._events) > 10000:
                    self._events = self._events[-10000:]
            return event
        except Exception:
            return None

    def trace_decision(
        self,
        payment: Any,
        events: List[Any],
        order_events: Optional[List[Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[DecisionTrace]:
        """Build a full end-to-end decision trace. Never raises."""
        try:
            tracer = DecisionTracer(correlation_id=correlation_id)
            return tracer.trace_payment(payment, events, order_events)
        except Exception as e:
            return None

    def health_check(self) -> SystemHealthReport:
        """Run a full system health check. Always returns a report."""
        try:
            return self._health_checker.check()
        except Exception as e:
            from .models import HealthStatus
            return SystemHealthReport(
                overall_status=HealthStatus.UNHEALTHY,
                critical_failures=["HealthChecker failed"],
                non_critical_failures=[],
            )

    def get_latency_metrics(self, operation: Optional[str] = None) -> Dict:
        """Return latency metrics. Never raises."""
        try:
            if operation:
                return {operation: self._recorder.get_metrics(operation).model_dump()}
            return {op: m.model_dump() for op, m in self._recorder.get_all_metrics().items()}
        except Exception:
            return {}

    def get_recent_events(self, limit: int = 100) -> List[ObservabilityEvent]:
        """Return recent events. Never raises."""
        try:
            with self._lock:
                return list(self._events[-limit:])
        except Exception:
            return []

    def get_events_for_payment(self, payment_id: str) -> List[ObservabilityEvent]:
        """Return all events for a given payment_id. Never raises."""
        try:
            with self._lock:
                return [e for e in self._events if e.payment_id == payment_id]
        except Exception:
            return []


# Module-level singleton
_service: Optional[ObservabilityService] = None
_service_lock = threading.Lock()


def get_observability_service() -> ObservabilityService:
    """Return the global ObservabilityService singleton."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = ObservabilityService()
    return _service
