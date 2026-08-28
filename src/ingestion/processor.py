"""
Event Processor and Event Store for RecoverAI.
Handles end-to-end webhook validation, deduplication, state evaluation, and recovery dispatch.
"""

import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timezone
from state_engine.engine import FinancialStateEngine
from state_engine.models import PaymentRecord, Event
from agent.orchestrator import AgenticRecoveryOrchestrator
from audit.logger import AuditLogger
from .models import (
    WebhookPayload,
    IngestedEventRecord,
    IngestionResult,
    IngestionStatus,
)
from .parser import WebhookParser
from .normalizer import EventNormalizer


class EventProcessor:
    """
    Thread-safe event ingestion processor and timeline recorder.
    Ensures idempotency, chronological ordering, and immediate state re-evaluation.
    """

    def __init__(
        self,
        state_engine: Optional[FinancialStateEngine] = None,
        orchestrator: Optional[AgenticRecoveryOrchestrator] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.state_engine = state_engine or FinancialStateEngine()
        self.orchestrator = orchestrator or AgenticRecoveryOrchestrator(audit_logger=audit_logger)
        self.audit_logger = audit_logger or AuditLogger()

        self._lock = threading.Lock()
        self._seen_event_ids: Set[Tuple[str, str]] = set()  # (provider, event_id)
        self._payment_event_store: Dict[str, List[Event]] = {}  # payment_id -> List[Event]
        self._payment_raw_records: Dict[str, List[IngestedEventRecord]] = {}
        self._timeline_events: List[Dict[str, Any]] = []

    def clear_store(self) -> None:
        """Reset internal memory store for test isolation."""
        with self._lock:
            self._seen_event_ids.clear()
            self._payment_event_store.clear()
            self._payment_raw_records.clear()
            self._timeline_events.clear()

    def get_events_for_payment(self, payment_id: str) -> List[Event]:
        """Retrieve all ingested events for a payment sorted chronologically."""
        with self._lock:
            evs = self._payment_event_store.get(payment_id, [])
            return sorted(evs, key=lambda e: e.ts or "")

    def get_timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve latest events in the live ingestion timeline for the Command Center UI."""
        with self._lock:
            return list(reversed(self._timeline_events[-limit:]))

    def process_webhook(self, raw_payload: Dict[str, Any]) -> IngestionResult:
        """
        Main entry point for processing incoming webhook payloads.
        
        Pipeline:
        WEBHOOK -> VALIDATE -> NORMALIZE -> DEDUPLICATE -> UPDATE EVENT STORE -> STATE ENGINE -> RECOVERY PIPELINE
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. VALIDATE & PARSE
        is_valid, parsed_payload, parse_err = WebhookParser.parse_payload(raw_payload)
        if not is_valid or parsed_payload is None:
            return IngestionResult(
                status=IngestionStatus.MALFORMED_EVENT,
                event_id=raw_payload.get("event_id", "unknown") if isinstance(raw_payload, dict) else "unknown",
                provider=raw_payload.get("provider", "mock") if isinstance(raw_payload, dict) else "mock",
                message=f"Webhook validation failed: {parse_err}",
                timestamp=now_iso,
            )

        provider = parsed_payload.provider
        event_id = parsed_payload.event_id
        pid = parsed_payload.payment_id
        oid = parsed_payload.order_id
        amt = parsed_payload.amount or 0.0

        with self._lock:
            # 2. DEDUPLICATE (Idempotency Check)
            dedup_key = (provider, event_id)
            if dedup_key in self._seen_event_ids:
                return IngestionResult(
                    status=IngestionStatus.DUPLICATE_EVENT,
                    event_id=event_id,
                    provider=provider,
                    payment_id=pid,
                    order_id=oid,
                    message=f"Duplicate event '{event_id}' from provider '{provider}' safely ignored.",
                    timestamp=now_iso,
                )

            # Record event key
            self._seen_event_ids.add(dedup_key)

            # 3. NORMALIZE
            normalized_event = EventNormalizer.normalize(parsed_payload)

            # 4. FETCH PREVIOUS STATE
            existing_events = list(self._payment_event_store.get(pid, []))
            payment_rec = PaymentRecord(
                payment_id=pid,
                order_id=oid,
                amount=amt,
                method=parsed_payload.method or "upi",
            )

            state_before = "NOT_FOUND"
            if existing_events:
                eval_before = self.state_engine.evaluate_payment(payment_rec, existing_events)
                state_before = eval_before.state.value

            # 5. UPDATE EVENT STORE
            if pid not in self._payment_event_store:
                self._payment_event_store[pid] = []
            self._payment_event_store[pid].append(normalized_event)

            # Keep chronologically sorted
            self._payment_event_store[pid].sort(key=lambda e: e.ts or "")
            updated_events = list(self._payment_event_store[pid])

            # Record raw record for audit preservation
            ingested_rec = IngestedEventRecord(
                event_id=event_id,
                provider=provider,
                normalized_event=normalized_event,
                raw_payload=parsed_payload.payload,
                received_at=now_iso,
            )
            if pid not in self._payment_raw_records:
                self._payment_raw_records[pid] = []
            self._payment_raw_records[pid].append(ingested_rec)

            # 6. EVALUATE FINANCIAL STATE ENGINE
            eval_after = self.state_engine.evaluate_payment(payment_rec, updated_events)
            state_after = eval_after.state.value
            state_changed = state_before != state_after

        # 7. DYNAMIC DISPATCH / RECOVERY PIPELINE
        orch_res_dict = None
        if state_after == "VERIFIED_LOST":
            orch_outcome = self.orchestrator.process_payment(payment_rec, updated_events)
            orch_res_dict = orch_outcome.model_dump()
            action_name = orch_outcome.agent_action or "NONE"
            verification_str = orch_outcome.verification_state
        else:
            action_name = "STOP" if state_after in ["ALREADY_RECOVERED", "UNCERTAIN"] else "ESCALATE"
            verification_str = state_after

        # Record in UI Timeline
        timeline_entry = {
            "time": normalized_event.ts or now_iso,
            "event": normalized_event.event,
            "payment_id": pid,
            "order_id": oid,
            "amount": amt,
            "source": provider,
            "state_before": state_before,
            "state_after": state_after,
            "state_changed": state_changed,
            "action": action_name,
            "verification": verification_str,
            "simulation": True,
        }
        with self._lock:
            self._timeline_events.append(timeline_entry)

        return IngestionResult(
            status=IngestionStatus.PROCESSED,
            event_id=event_id,
            provider=provider,
            payment_id=pid,
            order_id=oid,
            normalized_event=normalized_event,
            message=f"Event '{normalized_event.event}' processed. Financial state: '{state_after}'.",
            financial_state_before=state_before,
            financial_state_after=state_after,
            state_changed=state_changed,
            orchestrator_result=orch_res_dict,
            timestamp=now_iso,
        )
