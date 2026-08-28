====================================================
 RECOVERAI FULL DATASET EVALUATION REPORT
====================================================

**WARNING**: BUG DETECTED - CHECKSUM DOES NOT BALANCE!
Total processed: Rs. 6,150,100.00
Sum of 4 buckets: Rs. 3,725,571.00
Discrepancy: Rs. 2,424,529.00 missing from accounting.

**ERROR**: 171 payments failed to process.

====================================================
 A. VOLUME
====================================================
Total payments processed: 500
Total amount processed  : Rs. 6,150,100.00

====================================================
 B. FINANCIAL STATE ENGINE BREAKDOWN
====================================================
ALREADY_RECOVERED   :  261 (Rs. 2,855,239.00)
VERIFIED_LOST       :   17 (Rs. 5,283.00)
UNCERTAIN           :   22 (Rs. 307,678.00)
EXCEPTION           :   29 (Rs. 557,371.00)

Ground truth cross-check passed: 0 mismatches.

====================================================
 C. RECOVERY PIPELINE FUNNEL (VERIFIED_LOST)
====================================================
VERIFIED_LOST entered intelligence: 17
Scored RECOVERY_WORTHWHILE (+EV)  : 0
Scored DO_NOT_RECOVER (-EV)       : 17
Of RECOVERY_WORTHWHILE:
  -> APPROVED by Firewall         : 0
  -> BLOCKED by Firewall          : 0
Of APPROVED execution:
  -> SIMULATED_SUCCESS            : 0
  -> SIMULATED_FAILURE            : 0

====================================================
 D. THE FOUR HERO ACCOUNTING BUCKETS
====================================================
Rs. ACTUALLY RECOVERED : Rs. 0.00
Rs. CORRECTLY WITHHELD : Rs. 2,860,522.00
Rs. PENDING / WAITING  : Rs. 307,678.00
Rs. ESCALATED          : Rs. 557,371.00
----------------------------------------------------
Checksum Total         : Rs. 3,725,571.00
Total Amount Processed : Rs. 6,150,100.00
Difference             : Rs. 2,424,529.00

====================================================
 E. FIREWALL RULE FREQUENCY TABLE
====================================================
FIREWALL-006   : 261 blocks
FIREWALL-007   : 22 blocks
FIREWALL-002   : 17 blocks

====================================================
 F. RECOVERY EFFECTIVENESS
====================================================
Recovery attempts dispatched : 0
Real recovery rate           : N/A

====================================================
 G. UNNECESSARY ACTIONS AVOIDED
====================================================
Naive retries avoided on ALREADY_RECOVERED: 261

====================================================
 Execution Time: 3.23 seconds
====================================================

====================================================
 PROCESSING ERRORS TRACEBACKS (First 3)
====================================================

--- Payment ID: pay_9edbf54e7c7646 ---
Traceback (most recent call last):
  File "D:\recoryaiagent\run_full_dataset_evaluation.py", line 88, in run_evaluation
    outcome = orchestrator.process_payment(payment, pay_events, order_events=order_events)
  File "D:\recoryaiagent\src\agent\orchestrator.py", line 337, in process_payment
    verification = self.verifier.verify(
  File "D:\recoryaiagent\src\execution\verifier.py", line 56, in verify
    state_eval = self.state_engine.evaluate_payment(payment, full_events, full_order_events)
  File "D:\recoryaiagent\src\state_engine\engine.py", line 55, in evaluate_payment
    return evaluate_state_rules(
  File "D:\recoryaiagent\src\state_engine\rules.py", line 110, in evaluate_state_rules
    sorted_events, valid_ts = sort_events_chronologically(payment_events)
  File "D:\recoryaiagent\src\state_engine\rules.py", line 77, in sort_events_chronologically
    parsed_with_ev.sort(key=lambda x: x[0])
TypeError: can't compare offset-naive and offset-aware datetimes


--- Payment ID: pay_f9cd9fb5ff4046 ---
Traceback (most recent call last):
  File "D:\recoryaiagent\run_full_dataset_evaluation.py", line 88, in run_evaluation
    outcome = orchestrator.process_payment(payment, pay_events, order_events=order_events)
  File "D:\recoryaiagent\src\agent\orchestrator.py", line 337, in process_payment
    verification = self.verifier.verify(
  File "D:\recoryaiagent\src\execution\verifier.py", line 56, in verify
    state_eval = self.state_engine.evaluate_payment(payment, full_events, full_order_events)
  File "D:\recoryaiagent\src\state_engine\engine.py", line 55, in evaluate_payment
    return evaluate_state_rules(
  File "D:\recoryaiagent\src\state_engine\rules.py", line 110, in evaluate_state_rules
    sorted_events, valid_ts = sort_events_chronologically(payment_events)
  File "D:\recoryaiagent\src\state_engine\rules.py", line 77, in sort_events_chronologically
    parsed_with_ev.sort(key=lambda x: x[0])
TypeError: can't compare offset-naive and offset-aware datetimes


--- Payment ID: pay_07a26042e73549 ---
Traceback (most recent call last):
  File "D:\recoryaiagent\run_full_dataset_evaluation.py", line 88, in run_evaluation
    outcome = orchestrator.process_payment(payment, pay_events, order_events=order_events)
  File "D:\recoryaiagent\src\agent\orchestrator.py", line 337, in process_payment
    verification = self.verifier.verify(
  File "D:\recoryaiagent\src\execution\verifier.py", line 56, in verify
    state_eval = self.state_engine.evaluate_payment(payment, full_events, full_order_events)
  File "D:\recoryaiagent\src\state_engine\engine.py", line 55, in evaluate_payment
    return evaluate_state_rules(
  File "D:\recoryaiagent\src\state_engine\rules.py", line 110, in evaluate_state_rules
    sorted_events, valid_ts = sort_events_chronologically(payment_events)
  File "D:\recoryaiagent\src\state_engine\rules.py", line 77, in sort_events_chronologically
    parsed_with_ev.sort(key=lambda x: x[0])
TypeError: can't compare offset-naive and offset-aware datetimes
