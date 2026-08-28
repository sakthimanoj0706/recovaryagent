import React from 'react';
import { HelpCircle, CheckCircle, ShieldAlert, Sparkles, AlertCircle, FileSearch } from 'lucide-react';
import { ClosedLoopOutcome } from '../types';

interface WhyDidWeActPanelProps {
  outcome: ClosedLoopOutcome | null;
}

export const WhyDidWeActPanel: React.FC<WhyDidWeActPanelProps> = ({ outcome }) => {
  if (!outcome) {
    return (
      <div className="glass-card rounded-2xl p-6 border border-white/10 flex flex-col items-center justify-center min-h-[300px] text-center text-slate-500">
        <FileSearch className="w-10 h-10 text-slate-600 mb-2 animate-pulse" />
        <div className="text-sm font-medium text-slate-400">No active recovery outcome selected</div>
        <div className="text-xs text-slate-600 mt-1 max-w-sm">
          Run a scenario from the simulator or click any payment record below to inspect the decision reasoning.
        </div>
      </div>
    );
  }

  // Derive explicit explainability blocks
  const stateReason = outcome.initial_state === 'VERIFIED_LOST'
    ? 'State Engine evaluated complete payment & order history. No valid authorization or settlement was recorded.'
    : outcome.initial_state === 'ALREADY_RECOVERED'
    ? 'State Engine discovered a late AUTHORIZED or CAPTURED event. Money is safe; recovery is prohibited.'
    : outcome.initial_state === 'UNCERTAIN'
    ? 'Payment is currently pending at the gateway/bank. Awaiting asynchronous clearing.'
    : 'Irreconcilable settlement discrepancy or refund without capture. Escalated to ops.';

  const econReason = outcome.expected_net_value && outcome.expected_net_value > 0
    ? `Expected Net Value is positive (+₹${outcome.expected_net_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}). Probability (${intProb(outcome.recovery_probability)}%) outweighs intervention costs.`
    : outcome.expected_net_value !== undefined && outcome.expected_net_value <= 0
    ? `Expected Net Value is negative (₹${outcome.expected_net_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}). Pursuit would be economically irrational.`
    : 'Not evaluated for non-lost financial states.';

  const agentReason = outcome.agent_reason || (
    outcome.agent_action === 'PAYMENT_LINK'
      ? 'Soft failure detected. Direct payment link offers a fresh payment session without duplicate auth attempts.'
      : outcome.agent_action === 'RETRY'
      ? 'Transient gateway timeout detected. Safe to retry within policy retry ceiling.'
      : 'Policy prohibits intervention on this payment.'
  );

  const firewallReason = outcome.firewall_reason || (
    outcome.firewall_decision === 'APPROVED'
      ? 'State confirmed lost + positive ENV + action permitted under safety rules.'
      : `Halted by rule ${outcome.firewall_rule || 'POLICY'}. Action blocked to protect customer experience.`
  );

  function intProb(p?: number): number {
    return p ? Math.round(p * 100) : 0;
  }

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      <div className="flex items-center justify-between mb-5 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2 font-mono">
            <HelpCircle className="w-4 h-4 text-cyan-400" />
            WHY DID RECOVERAI ACT?
          </h2>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Transparent multi-layer decision rationale and explainability breakdown
          </p>
        </div>
        <div className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-white/10">
          ID: <span className="text-white font-bold">{outcome.payment_id}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Layer 1: Financial State */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                1. Financial State
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                outcome.initial_state === 'VERIFIED_LOST' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                outcome.initial_state === 'ALREADY_RECOVERED' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}>
                {outcome.initial_state}
              </span>
            </div>
            <div className="text-xs text-slate-300 leading-relaxed">
              {stateReason}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-white/5 text-[10px] font-mono text-slate-500">
            Source: Deterministic Financial State Engine
          </div>
        </div>

        {/* Layer 2: Economic Reasoning */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                2. Economic Reasoning
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                outcome.expected_net_value && outcome.expected_net_value > 0
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-slate-800 text-slate-400'
              }`}>
                ENV: {outcome.expected_net_value !== undefined ? `₹${outcome.expected_net_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A'}
              </span>
            </div>
            <div className="text-xs text-slate-300 leading-relaxed">
              {econReason}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-white/5 text-[10px] font-mono text-slate-500">
            Probability: {outcome.recovery_probability ? `${intProb(outcome.recovery_probability)}%` : 'N/A'} (Logistic Regression)
          </div>
        </div>

        {/* Layer 3: Agent Decision */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                3. Agent Strategy
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/30">
                {outcome.agent_action || 'STOP'}
              </span>
            </div>
            <div className="text-xs text-slate-300 leading-relaxed">
              {agentReason}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-white/5 text-[10px] font-mono text-slate-500">
            Advisory: LLM Planner (Gemini / OpenRouter)
          </div>
        </div>

        {/* Layer 4: Recovery Firewall */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-white/5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                4. Firewall Decision
              </span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${
                outcome.firewall_decision === 'APPROVED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}>
                {outcome.firewall_decision}
              </span>
            </div>
            <div className="text-xs text-slate-300 leading-relaxed">
              {firewallReason}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-white/5 text-[10px] font-mono text-slate-500">
            Enforced by: Recovery Firewall (Rules 001 - 010)
          </div>
        </div>
      </div>
    </div>
  );
};
