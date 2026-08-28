"""
Real-Time Event Ingestion and Webhook Processing for RecoverAI.
"""

from typing import Optional
from .models import (
    IngestionStatus,
    WebhookPayload,
    IngestedEventRecord,
    IngestionResult,
)
from .parser import WebhookParser
from .normalizer import EventNormalizer
from .processor import EventProcessor

_DEFAULT_PROCESSOR: Optional[EventProcessor] = None


def get_event_processor() -> EventProcessor:
    """Singleton getter for shared EventProcessor instance."""
    global _DEFAULT_PROCESSOR
    if _DEFAULT_PROCESSOR is None:
        _DEFAULT_PROCESSOR = EventProcessor()
    return _DEFAULT_PROCESSOR


__all__ = [
    "IngestionStatus",
    "WebhookPayload",
    "IngestedEventRecord",
    "IngestionResult",
    "WebhookParser",
    "EventNormalizer",
    "EventProcessor",
    "get_event_processor",
]
