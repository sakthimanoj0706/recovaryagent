"""
FinancialStateEngine: Core orchestration engine for RecoverAI.
"""

import math
from typing import List, Dict, Optional, Union, Any
from collections import defaultdict
from .models import FinancialState, RecommendedAction, Event, PaymentRecord, StateEvaluationResult
from .rules import evaluate_state_rules, sort_events_chronologically


def _clean_nan(data: Dict[str, Any]) -> Dict[str, Any]:
    """Replace float NaN with None for clean model instantiation."""
    cleaned = {}
    for k, v in data.items():
        if isinstance(v, float) and math.isnan(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


class FinancialStateEngine:
    """
    Deterministic, auditable engine for evaluating payment and order financial states.
    Strictly upholds: FAILED != LOST.
    """

    def __init__(self, evaluation_timestamp: Optional[str] = None):
        self.evaluation_timestamp = evaluation_timestamp

    def _normalize_payment(self, payment: Union[PaymentRecord, Dict[str, Any]]) -> PaymentRecord:
        if isinstance(payment, PaymentRecord):
            return payment
        return PaymentRecord(**_clean_nan(payment))

    def _normalize_event(self, event: Union[Event, Dict[str, Any]]) -> Event:
        if isinstance(event, Event):
            return event
        return Event(**_clean_nan(event))

    def evaluate_payment(
        self,
        payment: Union[PaymentRecord, Dict[str, Any]],
        events: Optional[List[Union[Event, Dict[str, Any]]]] = None,
        order_events: Optional[List[Union[Event, Dict[str, Any]]]] = None,
    ) -> StateEvaluationResult:
        """
        Evaluate the financial state of a single payment record given its events and order events.
        """
        norm_payment = self._normalize_payment(payment)
        norm_events = [self._normalize_event(e) for e in (events or [])]
        norm_order_events = [self._normalize_event(e) for e in (order_events or [])] if order_events else None

        return evaluate_state_rules(
            payment=norm_payment,
            payment_events=norm_events,
            order_events=norm_order_events,
            evaluation_ts=self.evaluation_timestamp,
        )

    def evaluate_all(
        self,
        payments: List[Union[PaymentRecord, Dict[str, Any]]],
        events: List[Union[Event, Dict[str, Any]]],
    ) -> List[StateEvaluationResult]:
        """
        Evaluate a batch of payments and their event history.
        Efficiently indexes events by payment_id and order_id before running deterministic rules.
        """
        norm_payments = [self._normalize_payment(p) for p in payments]
        norm_events = [self._normalize_event(e) for e in events]

        events_by_pay: Dict[str, List[Event]] = defaultdict(list)
        events_by_order: Dict[str, List[Event]] = defaultdict(list)

        for ev in norm_events:
            if ev.payment_id:
                events_by_pay[ev.payment_id].append(ev)
            if ev.order_id:
                events_by_order[ev.order_id].append(ev)

        results = []
        for pay in norm_payments:
            pay_evs = events_by_pay.get(pay.payment_id, [])
            ord_evs = events_by_order.get(pay.order_id, []) if pay.order_id else []
            res = evaluate_state_rules(
                payment=pay,
                payment_events=pay_evs,
                order_events=ord_evs,
                evaluation_ts=self.evaluation_timestamp,
            )
            results.append(res)

        return results
