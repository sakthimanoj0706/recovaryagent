import React from 'react';
import {
  ShieldCheck,
  TrendingUp,
  Brain,
  Lock,
  Zap,
  CheckCircle2,
  AlertCircle,
  Clock,
  HelpCircle,
  Sparkles,
  ArrowDown,
  Info,
  Check,
  X,
} from 'lucide-react';
import { AgentDecisionTrace as IAgentDecisionTrace, ClosedLoopOutcome } from '../types';

interface AgentDecisionTraceProps {
  trace?: IAgentDecisionTrace | null;
  outcome?: ClosedLoopOutcome | null;
}

export const AgentDecisionTrace: React.FC<AgentDecisionTraceProps> = ({ trace, outcome }) => {
  // If trace is not directly provided, derive structured stages from active outcome
  const t: IAgentDecisionTrace | null =
    trace ||
    (outcome
      ? {
          payment_id: outcome.payment_id,
          order_id: outcome.order_id,
          amount: outcome.amount,
          prove: {
            financial_state: outcome.initial_state,
            state_rule_id:
              outcome.initial_state === 'ALREADY_RECOVERED'
                ? 'STATE-RULE-001'
                : outcome.initial_state === 'UNCERTAIN'
                ? 'STATE-RULE-004'
                : outcome.initial_state === 'EXCEPTION'
                ? 'STATE-RULE-000'
                : 'STATE-RULE-005',
            state_reason:
              outcome.initial_state === 'ALREADY_RECOVERED'
                ? 'Late authorization detected; payment captured.'
                : outcome.initial_state === 'UNCERTAIN'
                ? 'Payment within active uncertainty window; awaiting asynchronous clearing.'
                : outcome.initial_state === 'EXCEPTION'
                ? 'Reconciliation mismatch or invalid state transition.'
                : 'Confirmed terminal failure with no subsequent capture.',
          },
          prioritize: {
            recovery_probability: outcome.recovery_probability,
            expected_net_value: outcome.expected_net_value,
            economic_decision:
              outcome.initial_state !== 'VERIFIED_LOST'
                ? 'BYPASSED'
                : (outcome.expected_net_value || 0) > 0
                ? 'RECOVERY_WORTHWHILE'
                : 'DO_NOT_RECOVER',
          },
          plan: {
            agent_action:
              outcome.initial_state !== 'VERIFIED_LOST'
                ? 'BYPASSED'
                : outcome.agent_action || 'STOP',
            agent_reason:
              outcome.agent_reason ||
              (outcome.initial_state !== 'VERIFIED_LOST'
                ? 'Financial state does not permit recovery planning.'
                : 'Action selected according to failure policy.'),
            agent_mode: 'demo',
          },
          guard: {
            firewall_decision: outcome.firewall_decision,
            firewall_rule_id: outcome.firewall_rule,
            firewall_reason: outcome.firewall_reason || 'Firewall policy evaluated.',
          },
          act: {
            execution_id: outcome.execution_id,
            execution_status: outcome.execution_id
              ? outcome.execution_status
              : outcome.firewall_decision === 'STOP' || outcome.firewall_decision === 'ESCALATE'
              ? 'BLOCKED_BY_FIREWALL'
              : 'NOT_EXECUTED',
          },
          verify: {
            verification_state: outcome.verification_state,
            verification_source: outcome.source_of_truth || 'FINANCIAL STATE ENGINE',
            final_result: outcome.final_outcome,
          },
          accounting: {
            amount_recovered: outcome.amount_recovered,
            amount_withheld: outcome.amount_withheld,
            amount_pending: outcome.final_outcome === 'WAIT' ? outcome.amount : 0,
            amount_escalated: outcome.final_outcome === 'ESCALATED_TO_OPERATIONS' ? outcome.amount : 0,
          },
          timestamp: new Date().toISOString(),
        }
      : null);

  if (!t) {
    return (
      <div className="rounded-2xl bg-slate-900/60 border border-white/5 p-6 backdrop-blur-md text-center text-slate-400">
        <Info className="w-8 h-8 mx-auto mb-2 text-cyan-400 opacity-60" />
        <p className="text-sm font-mono">Run a recovery workflow or scenario to view the 6-stage structured decision trace.</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-950/95 border border-white/10 p-6 backdrop-blur-xl shadow-2xl space-y-6 font-mono">
      {/* Header with Title and Prominent AI Boundary Badges */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <h2 className="text-base font-bold text-white tracking-wide uppercase">
              Agent Decision Trace &amp; Safety Proof
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Deterministic 6-stage telemetry for Payment <span className="text-cyan-300 font-semibold">{t.payment_id}</span> (₹{t.amount.toLocaleString('en-IN')})
          </p>
        </div>

        {/* Badges */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="px-2.5 py-1 rounded-md bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <Sparkles className="w-3.5 h-3.5" />
            AI ADVISORY ONLY
          </span>
          <span className="px-2.5 py-1 rounded-md bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <ShieldCheck className="w-3.5 h-3.5" />
            FINANCIAL TRUTH = STATE ENGINE
          </span>
          <span className="px-2.5 py-1 rounded-md bg-amber-500/15 border border-amber-500/30 text-amber-300 text-[11px] font-semibold">
            {t.plan.agent_mode === 'live' ? '⚡ LIVE FRONTIER AI' : '🔒 DEMO / CACHED AI'}
          </span>
        </div>
      </div>

      {/* AI Boundary Checklist Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 rounded-xl bg-slate-950/70 border border-white/5 text-xs">
        <div className="space-y-1.5 border-r border-white/5 pr-3">
          <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
            <Check className="w-3.5 h-3.5" /> AI Authority Scope (Advisory)
          </span>
          <ul className="space-y-1 text-slate-300 text-[11px]">
            <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> Analyze structured failure context</li>
            <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> Recommend safest recovery intervention</li>
            <li className="flex items-center gap-1.5"><span className="text-emerald-400">✓</span> Provide auditable structured rationale</li>
          </ul>
        </div>
        <div className="space-y-1.5 pl-1">
          <span className="text-[11px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1">
            <X className="w-3.5 h-3.5" /> Non-Negotiable Hard Boundaries
          </span>
          <ul className="space-y-1 text-slate-400 text-[11px]">
            <li className="flex items-center gap-1.5"><span className="text-rose-400">✕</span> Cannot modify financial state or ENV</li>
            <li className="flex items-center gap-1.5"><span className="text-rose-400">✕</span> Cannot bypass deterministic firewall rules</li>
            <li className="flex items-center gap-1.5"><span className="text-rose-400">✕</span> Cannot declare financial recovery (Verifier only)</li>
          </ul>
        </div>
      </div>

      {/* 6-Stage Timeline Vertical Flow */}
      <div className="space-y-3 pt-2">
        {/* STAGE 1: PROVE */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10 relative">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[11px] font-bold">STAGE 1: PROVE</span>
              <span className="text-white font-bold text-xs">Financial State Engine</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-extrabold border border-emerald-500/30">LEDGER TRUTH</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-cyan-300 font-semibold">{t.prove.state_rule_id || 'STATE-RULE'}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-extrabold ${
                t.prove.financial_state === 'VERIFIED_LOST'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : t.prove.financial_state === 'ALREADY_RECOVERED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : t.prove.financial_state === 'UNCERTAIN'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
              }`}>
                {t.prove.financial_state}
              </span>
            </div>
          </div>
          <p className="text-xs text-slate-300 mt-2 font-sans">{t.prove.state_reason}</p>
        </div>

        <div className="flex justify-center -my-1 text-slate-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* STAGE 2: PRIORITIZE */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-[11px] font-bold">STAGE 2: PRIORITIZE</span>
              <span className="text-white font-bold text-xs">Recovery Intelligence &amp; Economics</span>
              <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-400 text-[10px] font-extrabold border border-indigo-500/30">POLICY</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
              t.prioritize.economic_decision === 'RECOVERY_WORTHWHILE'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-slate-800 text-slate-400 border border-slate-700'
            }`}>
              {t.prioritize.economic_decision}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 mt-2 text-xs">
            <div>
              <span className="text-slate-500 text-[11px]">Recovery Probability: </span>
              <span className="text-slate-200 font-bold">
                {t.prioritize.recovery_probability !== null && t.prioritize.recovery_probability !== undefined
                  ? `${(t.prioritize.recovery_probability * 100).toFixed(1)}%`
                  : 'BYPASSED'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 text-[11px]">Expected Net Value: </span>
              <span className={`font-bold ${
                (t.prioritize.expected_net_value || 0) > 0 ? 'text-emerald-300' : 'text-slate-400'
              }`}>
                {t.prioritize.expected_net_value !== null && t.prioritize.expected_net_value !== undefined
                  ? `₹${t.prioritize.expected_net_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                  : 'BYPASSED'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex justify-center -my-1 text-slate-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* STAGE 3: PLAN */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[11px] font-bold">STAGE 3: PLAN</span>
              <span className="text-white font-bold text-xs">Agentic Recovery Planner</span>
              <span className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 text-[10px] font-extrabold border border-amber-500/30">AI ADVISORY</span>
            </div>
            <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-xs font-bold border border-cyan-500/30">
              {t.plan.agent_action}
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-2 font-sans italic">
            &ldquo;{t.plan.agent_reason}&rdquo;
          </p>
        </div>

        <div className="flex justify-center -my-1 text-slate-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* STAGE 4: GUARD */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[11px] font-bold">STAGE 4: GUARD</span>
              <span className="text-white font-bold text-xs">Deterministic Recovery Firewall</span>
              <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 text-[10px] font-extrabold border border-rose-500/30">FIREWALL</span>
            </div>
            <div className="flex items-center gap-2">
              {t.guard.firewall_rule_id && (
                <span className="text-[11px] text-rose-300 font-semibold">{t.guard.firewall_rule_id}</span>
              )}
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                t.guard.firewall_decision === 'APPROVED'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                  : t.guard.firewall_decision === 'STOP'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
              }`}>
                {t.guard.firewall_decision}
              </span>
            </div>
          </div>
          <p className="text-xs text-slate-300 mt-2 font-sans">{t.guard.firewall_reason}</p>
        </div>

        <div className="flex justify-center -my-1 text-slate-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* STAGE 5: ACT */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[11px] font-bold">STAGE 5: ACT</span>
              <span className="text-white font-bold text-xs">Simulated Action Executor</span>
              <span className="px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 text-[10px] font-extrabold border border-cyan-500/30">EXECUTOR</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
              t.act.execution_status === 'SIMULATED_SUCCESS'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : t.act.execution_status === 'SIMULATED_FAILURE'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {t.act.execution_status}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Execution ID: <span className="text-slate-200">{t.act.execution_id || 'NONE (Blocked / Bypassed)'}</span>
          </div>
        </div>

        <div className="flex justify-center -my-1 text-slate-600">
          <ArrowDown className="w-4 h-4" />
        </div>

        {/* STAGE 6: VERIFY */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-white/10">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[11px] font-bold">STAGE 6: VERIFY</span>
              <span className="text-white font-bold text-xs">Closed-Loop Verification</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-extrabold border border-emerald-500/30">LEDGER TRUTH</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-xs font-extrabold ${
              t.verify.final_result === 'RECOVERY_SUCCESS'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : t.verify.final_result === 'RECOVERY_FAILED'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }`}>
              {t.verify.final_result}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 mt-1">
            Source of Truth: <span className="text-cyan-300 font-semibold">{t.verify.verification_source}</span> | Verified State: <span className="text-white font-bold">{t.verify.verification_state}</span>
          </div>
        </div>
      </div>

      {/* Final Accounting Breakdown (4 Distinct Buckets) */}

      <div className="pt-4 border-t border-white/10">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
          Final Financial Accounting Breakdown
        </h4>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-center">
            <span className="text-[10px] text-emerald-400 uppercase font-bold block">₹ Recovered</span>
            <span className="text-sm font-extrabold text-emerald-300">
              ₹{t.accounting.amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-center">
            <span className="text-[10px] text-cyan-400 uppercase font-bold block">₹ Withheld</span>
            <span className="text-sm font-extrabold text-cyan-300">
              ₹{t.accounting.amount_withheld.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-500/30 text-center">
            <span className="text-[10px] text-amber-400 uppercase font-bold block">₹ Pending / Wait</span>
            <span className="text-sm font-extrabold text-amber-300">
              ₹{t.accounting.amount_pending.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-purple-950/40 border border-purple-500/30 text-center">
            <span className="text-[10px] text-purple-400 uppercase font-bold block">₹ Escalated</span>
            <span className="text-sm font-extrabold text-purple-300">
              ₹{t.accounting.amount_escalated.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
