"""
Compatibility re-export of AuditLogger.
"""

from audit.logger import AuditLogger
from audit.schemas import AuditRecord, SystemMetrics

__all__ = ["AuditLogger", "AuditRecord", "SystemMetrics"]
