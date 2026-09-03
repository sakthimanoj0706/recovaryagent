from typing import List, Dict, Any
from learning.models import RecoveryOutcome
import random

class OfflineDatasetBuilder:
    
    @staticmethod
    def build_dataset(outcomes: List[RecoveryOutcome], train_ratio: float = 0.7, val_ratio: float = 0.15) -> Dict[str, List[RecoveryOutcome]]:
        """
        Deterministically split outcomes into train/val/test for offline ML learning.
        Sort by timestamp to prevent temporal leakage.
        """
        sorted_outcomes = sorted(outcomes, key=lambda x: x.timestamp)
        n = len(sorted_outcomes)
        
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        return {
            "train": sorted_outcomes[:train_end],
            "val": sorted_outcomes[train_end:val_end],
            "test": sorted_outcomes[val_end:]
        }
