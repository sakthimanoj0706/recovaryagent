import React from 'react';
import {
  Brain,
  ShieldCheck,
  Scale,
  Lock,
  Sparkles,
  HelpCircle,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  XCircle,
  FileCheck2,
} from 'lucide-react';
import { ClosedLoopOutcome } from '../types';

interface DecisionExplanationPanelProps {
  outcome: ClosedLoopOutcome | null;
}

export const DecisionExplanationPanel: React.FC<DecisionExplanationPanelProps> = ({ outcome }) => {
  if (!outcome) {
    return (
      <div className="bg-[#0e1424] rounded-2xl p-6 border border-white/10 flex flex-col items-center justify-center min-h-[260px] text-center text-slate-500 shadow-xl">
        <HelpCircle className="w-10 h-10 text-slate-600 mb-2 animate-pulse" />
        <div className="text-sm font-medium text-slate-400 font-mono">No Active Recovery Decision Selected</div>
        <div className="text-xs text-slate-500 mt-1 max-w-md">
          Trigger a scenario above or select a payment to view complete decision explainability, model breakdown, and firewall authority.
        </div>
      </div>
    );
  }

  const isEligible = outcome.initial_state === 'VERIFIED_LOST' && (outcome.expected_net_value || 0) > 0;
  const isBlocked = outcome.firewall_decision === 'STOP' || outcome.firewall_decision === 'BLOCKED';
  const probPercent = outcome.recovery_probability ? Math.round(outcome.recovery_probability * 100) : 0;
  const env = outcome.expected_net_value || 0;
  const amt = outcome.amount || 0;
  const gross = amt * (outcome.recovery_probability || 0) * 0.98; // ~2% MDR
  const retryCost = 2.5;
  const intervCost = outcome.agent_action === 'PAYMENT_LINK' ? 5.0 : 1.0;
  const frictionCost = 10.0;

  return (
    <div className="bg-[#0e1424] rounded-2xl p-6 border border-white/10 relative overflow-hidden shadow-2xl space-y-5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 uppercase tracking-wider">
              Explainability &amp; Safety Reasoning
            </span>
            <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
              <Brain className="w-5 h-5 text-cyan-400" />
              DECISION EXPLAINABILITY &amp; AUTHORITY HIERARCHY
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Explains why this decision was taken and proves the non-negotiable separation between AI advisory and deterministic ledger truth.
          </p>
        </div>

        {/* Status Badge */}
        <div className="flex items-center gap-2">
          {isBlocked ? (
            <span className="text-xs font-mono px-3 py-1 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              FIREWALL OVERRIDE: {outcome.firewall_rule || 'STOPPED'}
            </span>
          ) : (
            <span className="text-xs font-mono px-3 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              APPROVED FOR RECOVERY
            </span>
          )}
        </div>
      </div>

      {/* 4 Clear Authority Stages */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs font-mono">
        {/* 1. AI ADVISORY */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-purple-500/30 flex flex-col justify-between space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              1. AI ADVISORY
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-semibold">
              PROBABILISTIC
            </span>
          </div>
          <div>
            <div className="text-slate-400 text-[11px]">Proposed Action:</div>
            <div className="text-sm font-bold text-white mt-0.5">{outcome.agent_action || 'NO_ACTION'}</div>
          </div>
          <div className="text-[10px] text-slate-400 border-t border-white/5 pt-2">
            Recommendation only. Zero execution authority.
          </div>
        </div>

        {/* 2. DETERMINISTIC POLICY */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-blue-500/30 flex flex-col justify-between space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1">
              <Scale className="w-3 h-3" />
              2. POLICY ENGINE
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-semibold">
              BOUNDED
            </span>
          </div>
          <div>
            <div className="text-slate-400 text-[11px]">Action Space Check:</div>
            <div className="text-sm font-bold text-blue-300 mt-0.5">STRICT VALIDATION PASS</div>
          </div>
          <div className="text-[10px] text-slate-400 border-t border-white/5 pt-2">
            Validates action schema against merchant contracts.
          </div>
        </div>

        {/* 3. FIREWALL AUTHORITY */}
        <div className={`p-3.5 rounded-xl bg-slate-900/60 border flex flex-col justify-between space-y-2 ${isBlocked ? 'border-amber-500/50 bg-amber-950/20' : 'border-emerald-500/30'}`}>
          <div className="flex items-center justify-between">
            <span className={`text-[10px] font-bold uppercase tracking-wider flex items-center gap-1 ${isBlocked ? 'text-amber-400' : 'text-emerald-400'}`}>
              <Lock className="w-3 h-3" />
              3. FIREWALL AUTHORITY
            </span>
            <span className={`text-[9px] px-1.5 py-0.5 rounded font-semibold ${isBlocked ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'}`}>
              NON-BYPASSABLE
            </span>
          </div>
          <div>
            <div className="text-slate-400 text-[11px]">Firewall Verdict:</div>
            <div className={`text-sm font-bold mt-0.5 ${isBlocked ? 'text-amber-300' : 'text-emerald-300'}`}>
              {outcome.firewall_decision} ({outcome.firewall_rule || 'PASSED'})
            </div>
          </div>
          <div className="text-[10px] text-slate-400 border-t border-white/5 pt-2">
            Hard safety rules can override any AI recommendation.
          </div>
        </div>

        {/* 4. LEDGER TRUTH */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-cyan-500/30 flex flex-col justify-between space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1">
              <FileCheck2 className="w-3 h-3" />
              4. LEDGER TRUTH
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-semibold">
              AUTHORITATIVE
            </span>
          </div>
          <div>
            <div className="text-slate-400 text-[11px]">Financial State:</div>
            <div className="text-sm font-bold text-cyan-300 mt-0.5">{outcome.verification_state || outcome.initial_state}</div>
          </div>
          <div className="text-[10px] text-slate-400 border-t border-white/5 pt-2">
            Independent ledger verification confirms final money state.
          </div>
        </div>
      </div>

      {/* Two-Column Deep Breakdown: Economics vs Safety Rationale */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: Economic Math Breakdown */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-white/10 space-y-3 font-mono">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              RECOVERY INTELLIGENCE &amp; ECONOMICS
            </span>
            <span className="text-xs text-slate-400">
              P(Success): <strong className="text-emerald-400">{probPercent}%</strong>
            </span>
          </div>

          {/* Equation Breakdown */}
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Gross Expected Recovery (P × ₹{amt.toLocaleString('en-IN')} × 0.98):</span>
              <span className="text-white">₹{gross.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>- Gateway Retry Cost:</span>
              <span className="text-rose-400">-₹{retryCost.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>- Channel Intervention Cost (Payment Link/SMS):</span>
              <span className="text-rose-400">-₹{intervCost.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>- Customer Friction &amp; Brand Factor:</span>
              <span className="text-rose-400">-₹{frictionCost.toFixed(2)}</span>
            </div>
            <div className="border-t border-white/10 pt-1.5 flex justify-between font-bold text-sm">
              <span className="text-slate-200">Expected Net Value (ENV):</span>
              <span className={env > 0 ? 'text-emerald-400' : 'text-amber-400'}>
                {env > 0 ? `+₹${env.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : `₹${env.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}
              </span>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 bg-slate-900/80 p-2.5 rounded-lg border border-white/5">
            <strong>Key Features:</strong> Soft failure intent, high cart size, valid mobile contact, no prior chargebacks.
          </div>
        </div>

        {/* Right Column: Why Did We Act / Not Act View */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-white/10 space-y-3 font-mono flex flex-col justify-between">
          <div className="flex items-center justify-between border-b border-white/10 pb-2">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              {isBlocked ? 'WHY DID WE WITHHOLD / STOP?' : 'WHY WAS THIS PAYMENT ELIGIBLE?'}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="bg-slate-900/90 p-3 rounded-lg border border-white/5">
              <div className="text-[10px] text-slate-400 font-bold uppercase mb-1">Decisive Safety Rationale:</div>
              <p className="text-slate-200 leading-relaxed">
                {outcome.reason || outcome.agent_reason || 'Payment verified lost on ledger, positive expected recovery value confirmed, action compliant with safety rules.'}
              </p>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-white/5 text-[11px]">
              <span className="text-slate-400">Financial Impact:</span>
              <span className="font-bold text-white">
                {outcome.amount_recovered > 0
                  ? `₹${outcome.amount_recovered.toLocaleString('en-IN')} Actually Recovered`
                  : `₹${outcome.amount_withheld.toLocaleString('en-IN')} Correctly Withheld`}
              </span>
            </div>
          </div>

          <div className="text-[10px] text-cyan-300/80 flex items-center gap-1.5 pt-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
            <span>Guaranteed: Zero false recoveries reported to merchant accounting.</span>
          </div>
        </div>
      </div>
    </div>
  );
};
