"""
Immutable JSONL audit trail logger and metrics calculation for RecoverAI.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone
from .schemas import AuditRecord, SystemMetrics


DEFAULT_AUDIT_PATH = Path("logs") / "recovery_audit.jsonl"


class AuditLogger:
    """
    Appends structured, immutable audit entries to JSONL and aggregates system metrics.
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or DEFAULT_AUDIT_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: Union[AuditRecord, Dict[str, Any], Any]) -> Dict[str, Any]:
        """
        Append execution result to JSONL log file. Never overwrites existing records.
        """
        if isinstance(record, AuditRecord):
            entry = record.to_dict()
        elif hasattr(record, "model_dump"):
            dumped = record.model_dump()
            # Map ClosedLoopOutcome fields if necessary
            entry = {
                "timestamp": dumped.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "payment_id": dumped.get("payment_id"),
                "order_id": dumped.get("order_id"),
                "initial_financial_state": dumped.get("initial_state") or dumped.get("initial_financial_state") or dumped.get("financial_state", "UNKNOWN"),
                "recovery_probability": dumped.get("recovery_probability"),
                "expected_net_value": dumped.get("expected_net_value"),
                "agent_action": dumped.get("agent_action"),
                "agent_reason": dumped.get("agent_reason"),
                "firewall_decision": dumped.get("firewall_decision"),
                "firewall_rule": dumped.get("firewall_rule"),
                "execution_id": dumped.get("execution_id"),
                "execution_status": dumped.get("execution_status"),
                "verification_state": dumped.get("verification_state"),
                "final_result": dumped.get("final_outcome") or dumped.get("final_result"),
                "simulation_flag": dumped.get("simulation_flag", True),
                "retry_count": dumped.get("retry_count", 0),
                "amount": float(dumped.get("amount", 0.0)),
                "amount_recovered": float(dumped.get("amount_recovered", 0.0)),
                "amount_withheld": float(dumped.get("amount_withheld", 0.0)),
            }
        elif isinstance(record, dict):
            entry = dict(record)
            if "timestamp" not in entry:
                entry["timestamp"] = datetime.now(timezone.utc).isoformat()
        else:
            entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "raw": str(record)}

        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return entry

    def get_records(self) -> List[AuditRecord]:
        """
        Read all persisted audit records from log file.
        """
        if not self.log_path.exists():
            return []

        records = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line.strip())
                        records.append(AuditRecord(**data))
                    except Exception:
                        continue
        return records

    def calculate_metrics(self, records: Optional[List[AuditRecord]] = None) -> SystemMetrics:
        """
        Compute hero metrics and system KPI counters across audit records.
        """
        recs = records if records is not None else self.get_records()

        metrics = SystemMetrics(total_cases=len(recs))

        for r in recs:
            # Verified Lost cases
            if r.initial_financial_state == "VERIFIED_LOST":
                metrics.verified_lost_cases += 1

            # Recovery attempts
            if r.agent_action in ["RETRY", "PAYMENT_LINK", "REMINDER"] and r.firewall_decision == "APPROVED":
                metrics.recovery_attempts += 1
                metrics.total_amount_attempted += r.amount

            # Recovery successes vs failures
            if r.final_result == "RECOVERY_SUCCESS":
                metrics.successful_recoveries += 1
            elif r.final_result == "RECOVERY_FAILED":
                metrics.failed_recoveries += 1

            # Hero Metric 1: Amount Recovered
            metrics.total_amount_recovered += r.amount_recovered

            # Hero Metric 2: Amount Withheld
            metrics.total_amount_withheld += r.amount_withheld

            # Firewall blocks & safety counters
            if r.firewall_decision in ["STOP", "BLOCKED"]:
                metrics.firewall_blocks += 1

            if r.amount_withheld > 0 or r.initial_financial_state in ["ALREADY_RECOVERED", "UNCERTAIN"]:
                metrics.unnecessary_actions_avoided += 1

            if r.initial_financial_state == "UNCERTAIN" or r.verification_state == "UNCERTAIN":
                metrics.uncertain_cases += 1

            if r.initial_financial_state == "EXCEPTION" or r.verification_state == "EXCEPTION":
                metrics.exception_cases += 1

            if r.firewall_rule == "FIREWALL-005" or r.final_result == "MAX_RETRY_PROTECTION":
                metrics.max_retry_blocks += 1

            if r.firewall_rule == "FIREWALL-009" or r.final_result == "DUPLICATE_ACTION_BLOCKED":
                metrics.duplicate_action_blocks += 1

        if metrics.recovery_attempts > 0:
            metrics.recovery_success_rate = round(metrics.successful_recoveries / metrics.recovery_attempts, 4)
        else:
            metrics.recovery_success_rate = 0.0

        return metrics
