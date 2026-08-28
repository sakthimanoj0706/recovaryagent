export interface SystemMetrics {
  total_cases: number;
  verified_lost_cases: number;
  recovery_attempts: number;
  successful_recoveries: number;
  failed_recoveries: number;
  recovery_success_rate: number;
  total_amount_attempted: number;
  total_amount_recovered: number; // Hero Metric #1
  total_amount_withheld: number;  // Hero Metric #2
  unnecessary_actions_avoided: number;
  firewall_blocks: number;
  uncertain_cases: number;
  exception_cases: number;
  max_retry_blocks: number;
  duplicate_action_blocks: number;
}

export interface PaymentItem {
  payment_id: string;
  order_id?: string;
  amount: number;
  currency: string;
  method: string;
  customer_segment: string;
  error_code: string;
  hardness: string;
  financial_state: string;
  event_count: number;
}

export interface PipelineStep {
  step: 'PAYMENT' | 'PROVE' | 'PRIORITIZE' | 'AGENT' | 'FIREWALL' | 'ACT' | 'VERIFY';
  status: 'PENDING' | 'ACTIVE' | 'COMPLETED' | 'BLOCKED' | 'SKIPPED' | 'FAILED';
  label: string;
  detail: string;
  timestamp?: string;
}

export interface ClosedLoopOutcome {
  payment_id: string;
  order_id?: string;
  amount: number;
  initial_state: string;
  recovery_probability?: number;
  expected_net_value?: number;
  agent_action?: string;
  agent_reason?: string;
  confidence: number;
  firewall_decision: string;
  firewall_rule?: string;
  firewall_reason?: string;
  execution_id?: string;
  execution_status: string;
  execution_message?: string;
  verification_state: string;
  source_of_truth: string;
  final_outcome: string;
  amount_recovered: number;
  amount_withheld: number;
  reason: string;
  simulation_flag: boolean;
  retry_count: number;
}

export interface DemoScenarioResponse {
  title: string;
  description: string;
  outcome: ClosedLoopOutcome;
  timeline: PipelineStep[];
}

export interface AuditEntry {
  timestamp: string;
  payment_id: string;
  order_id?: string;
  initial_financial_state: string;
  recovery_probability?: number;
  expected_net_value?: number;
  agent_action?: string;
  agent_reason?: string;
  firewall_decision: string;
  firewall_rule?: string;
  execution_id?: string;
  execution_status: string;
  verification_state: string;
  final_result: string;
  simulation_flag: boolean;
  retry_count: number;
  amount: number;
  amount_recovered: number;
  amount_withheld: number;
}

export interface ProveStage {
  financial_state: string;
  state_rule_id?: string;
  state_reason: string;
}

export interface PrioritizeStage {
  recovery_probability?: number;
  expected_net_value?: number;
  economic_decision: string;
}

export interface PlanStage {
  agent_action: string;
  agent_reason: string;
  agent_mode: string;
}

export interface GuardStage {
  firewall_decision: string;
  firewall_rule_id?: string;
  firewall_reason: string;
}

export interface ActStage {
  execution_id?: string;
  execution_status: string;
}

export interface VerifyStage {
  verification_state: string;
  verification_source: string;
  final_result: string;
}

export interface AccountingStage {
  amount_recovered: number;
  amount_withheld: number;
  amount_pending: number;
  amount_escalated: number;
}

export interface AgentDecisionTrace {
  payment_id: string;
  order_id?: string;
  amount: number;
  prove: ProveStage;
  prioritize: PrioritizeStage;
  plan: PlanStage;
  guard: GuardStage;
  act: ActStage;
  verify: VerifyStage;
  accounting: AccountingStage;
  timestamp: string;
}

