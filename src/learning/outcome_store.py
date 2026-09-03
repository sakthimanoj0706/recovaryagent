from typing import List, Optional, Dict
import json
from .models import RecoveryOutcome

class OutcomeStore:
    """
    Deterministic in-memory mock store for RecoveryOutcomes.
    In a real system, this writes to a durable DB.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OutcomeStore, cls).__new__(cls)
            cls._instance.outcomes = []
        return cls._instance

    def record(self, outcome: RecoveryOutcome):
        self.outcomes.append(outcome)

    def get_all(self) -> List[RecoveryOutcome]:
        return self.outcomes

    def get_by_strategy(self, strategy_id: str) -> List[RecoveryOutcome]:
        return [o for o in self.outcomes if o.strategy_id == strategy_id]

    def clear(self):
        self.outcomes = []
