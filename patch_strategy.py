import re

with open("src/benchmark/strategies.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will write the Intelligent strategy block via python string manipulation
new_strategy = '''
class IntelligentRecoveryStrategy(RecoverAIRecoveryStrategy):
    """
    Intelligent Recovery Strategy evaluating the new Intelligence Module.
    """
    def execute_lifecycle(self, lifecycle: SyntheticLifecycle, costs: CostModelConfig) -> ExecutionResult:
        res = ExecutionResult()
        payment = lifecycle.payment
        amount = payment.amount
        events = lifecycle.events
        order_events = lifecycle.order_events

        # PROVE
        state_eval = self.state_engine.evaluate_payment(payment, events, order_events)
        fin_state = state_eval.state

        if fin_state == FinancialState.ALREADY_RECOVERED:
            rec_amt = state_eval.recovered_amount if state_eval.recovered_amount is not None else amount
            out_amt = state_eval.outstanding_amount if state_eval.outstanding_amount is not None else max(0.0, amount - rec_amt)
            if lifecycle.is_refunded or lifecycle.has_late_capture or lifecycle.archetype.value in ("ALREADY_RECOVERED", "DUPLICATE", "OUT_OF_ORDER", "LATE_CAPTURE"):
                res.already_rec_protected = True
                res.recovered_amount = rec_amt
                res.outstanding_amount = out_amt
                if lifecycle.is_refunded:
                    res.withheld_amount = amount
                return res
            res.recovered_amount = rec_amt
            res.outstanding_amount = out_amt
            return res

        if fin_state == FinancialState.UNCERTAIN:
            res.pending_amount = amount
            return res
        if fin_state == FinancialState.EXCEPTION:
            res.escalated_amount = amount
            res.manual_escalations += 1
            return res

        res.is_opportunity = True
        
        # PRIORITIZE & PLAN using Intelligence Module
        from intelligence.service import IntelligentRecoveryService
        intel_service = IntelligentRecoveryService(model=self.prob_model)
        
        # Overwrite cost config to match benchmark
        intel_service.candidate_generator.config.payment_link_cost = costs.payment_link_cost
        intel_service.candidate_generator.config.reminder_cost = costs.customer_contact_cost
        intel_service.candidate_generator.config.retry_cost = costs.payment_link_cost
        intel_service.candidate_generator.config.escalation_cost = costs.manual_review_cost
        intel_service.candidate_generator.config.chargeback_risk_cost = costs.chargeback_risk_cost
        
        decision = intel_service.decide(payment, events, 0)
        
        # GUARD
        failure_event = next((e for e in reversed(events) if e.event == "payment.failed"), None)
        ctx = RecoveryContext(
            payment_id=payment.payment_id,
            amount=amount,
            method=payment.method,
            customer_segment=payment.customer_segment or "standard",
            financial_state=fin_state.value,
            recovery_probability=decision.deterministic_best_action.expected_recovery_probability,
            expected_net_value=decision.deterministic_best_action.expected_net_value,
            failure_reason=decision.classification.reason,
            hardness="hard" if decision.classification.failure_type.value == "HARD_DECLINE" else "soft",
            retry_count=0,
            previous_attempts=0,
            previous_actions=[],
        )
        
        try:
            plan = RecoveryPlan(
                payment_id=payment.payment_id,
                action=RecoveryAction(decision.selected_action),
                priority=RecoveryPriority.MEDIUM,
                reason=decision.selection_reason,
                confidence=1.0,
            )
        except ValueError:
            plan = RecoveryPlan(
                payment_id=payment.payment_id,
                action=RecoveryAction.STOP,
                priority=RecoveryPriority.MEDIUM,
                reason="Invalid LLM fallback",
                confidence=0.0
            )
        
        firewall_verdict = self.firewall.validate_action(context=ctx, plan=plan)

        if firewall_verdict.status != FirewallDecision.APPROVED:
            res.withheld_amount = amount
            if firewall_verdict.rule_id == "FIREWALL-004":
                res.hard_decline_prevented = True
            elif firewall_verdict.rule_id == "FIREWALL-009":
                res.duplicate_prevented = True
            return res

        res.attempted = True
        action_to_exec = firewall_verdict.action or plan.action
        
        if action_to_exec == RecoveryAction.RETRY:
            res.gateway_retries += 1
        elif action_to_exec == RecoveryAction.PAYMENT_LINK:
            res.payment_links += 1
            res.customer_contacts += 1
        elif action_to_exec == RecoveryAction.REMINDER:
            res.customer_contacts += 1
        elif action_to_exec == RecoveryAction.ESCALATE:
            res.manual_escalations += 1
        elif action_to_exec == RecoveryAction.STOP:
            res.withheld_amount = amount
            res.attempted = False
            return res

        sim_outcome = self.simulator.simulate_action(action_to_exec, lifecycle)
        if sim_outcome.success:
            res.succeeded = True
            res.recovered_amount = amount
        else:
            res.failed = True
            res.outstanding_amount = amount
            
        return res
'''
content = content + "\n\n" + new_strategy
with open("src/benchmark/strategies.py", "w", encoding="utf-8") as f:
    f.write(content)
