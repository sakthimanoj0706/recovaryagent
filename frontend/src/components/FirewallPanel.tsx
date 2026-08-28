import React from 'react';
import { ShieldAlert, ShieldCheck, Lock, AlertOctagon, CheckCircle2, RefreshCw, AlertTriangle, ArrowRight } from 'lucide-react';
import { ClosedLoopOutcome } from '../types';

interface FirewallPanelProps {
  outcome: ClosedLoopOutcome | null;
}

interface FirewallRuleInfo {
  id: string;
  name: string;
  trigger: string;
  verdict: 'STOP' | 'WAIT' | 'ESCALATE';
  description: string;
  color: string;
}

const FIREWALL_RULES: FirewallRuleInfo[] = [
  {
    id: 'FIREWALL-002',
    name: 'Negative Expected Net Value',
    trigger: 'ENV ≤ 0.0',
    verdict: 'STOP',
    description: 'Halts recovery if unit recovery costs exceed mathematical expected return.',
    color: 'amber',
  },
  {
    id: 'FIREWALL-004',
    name: 'Hard Decline Retry Block',
    trigger: 'hardness == "hard" && action == RETRY',
    verdict: 'STOP',
    description: 'Prohibits automated retries on permanent card blocks, stolen cards, or expired accounts.',
    color: 'rose',
  },
  {
    id: 'FIREWALL-005',
    name: 'Maximum Retry Threshold',
    trigger: 'retry_count ≥ 3',
    verdict: 'STOP',
    description: 'Strict limit of 3 retries per payment to avoid customer spam and bank penalty fees.',
    color: 'red',
  },
  {
    id: 'FIREWALL-006',
    name: 'Already Recovered Invariant',
    trigger: 'state == ALREADY_RECOVERED',
    verdict: 'STOP',
    description: 'Intercepts late-auth flip-flops to prevent double-charging already captured payments.',
    color: 'emerald',
  },
  {
    id: 'FIREWALL-007',
    name: 'Uncertain State Hold',
    trigger: 'state == UNCERTAIN',
    verdict: 'WAIT',
    description: 'Suspends recovery interventions while payment is in-flight in bank clearing window.',
    color: 'blue',
  },
  {
    id: 'FIREWALL-008',
    name: 'Settlement Discrepancy Escalation',
    trigger: 'state == EXCEPTION',
    verdict: 'ESCALATE',
    description: 'Routes un-reconciled amount discrepancies or abnormal events to human operations.',
    color: 'purple',
  },
  {
    id: 'FIREWALL-009',
    name: 'Duplicate Action Protection',
    trigger: 'action already executed',
    verdict: 'STOP',
    description: 'Guarantees idempotency by preventing identical duplicate links or retries within time window.',
    color: 'amber',
  },
];

export const FirewallPanel: React.FC<FirewallPanelProps> = ({ outcome }) => {
  const activeRuleId = outcome?.firewall_rule;

  return (
    <div className="bg-[#0e1424] rounded-2xl p-6 border border-white/10 relative overflow-hidden shadow-2xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30">
            <Lock className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                Deterministic Safety Rails
              </span>
              <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                RECOVERY FIREWALL RULE INVENTORY
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Hard non-bypassable constraints evaluated in deterministic Python before any gateway dispatch.
            </p>
          </div>
        </div>

        {outcome && (
          <div className="text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 flex items-center gap-2">
            <span className="text-slate-400">Current Evaluation:</span>
            <span className={`font-bold ${outcome.firewall_decision === 'APPROVED' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {outcome.firewall_decision} ({outcome.firewall_rule || 'PASSED'})
            </span>
          </div>
        )}
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        {FIREWALL_RULES.map((rule) => {
          const isTriggered = activeRuleId === rule.id;

          return (
            <div
              key={rule.id}
              className={`p-4 rounded-xl border transition-all relative overflow-hidden flex flex-col justify-between space-y-2 ${
                isTriggered
                  ? 'bg-amber-950/40 border-amber-400/80 shadow-lg shadow-amber-950/50 scale-[1.02]'
                  : 'bg-slate-900/50 border-white/5 opacity-80 hover:opacity-100'
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${isTriggered ? 'bg-amber-400 animate-ping' : 'bg-slate-600'}`} />
                  {rule.id}
                </span>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase ${
                    rule.verdict === 'STOP'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : rule.verdict === 'WAIT'
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                      : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  }`}
                >
                  {rule.verdict}
                </span>
              </div>

              {/* Title & Trigger */}
              <div>
                <h4 className="text-xs font-semibold text-slate-200 font-mono">{rule.name}</h4>
                <div className="text-[10px] font-mono text-cyan-400/90 mt-0.5 bg-slate-950/60 px-2 py-1 rounded border border-white/5">
                  Condition: <code>{rule.trigger}</code>
                </div>
              </div>

              {/* Description */}
              <p className="text-[11px] text-slate-400 leading-relaxed font-sans">{rule.description}</p>

              {/* Active Badge */}
              {isTriggered && (
                <div className="pt-2 border-t border-amber-500/30 flex items-center justify-between text-[10px] font-mono text-amber-300 font-bold">
                  <span className="flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    ACTIVELY FIRED IN THIS RUN
                  </span>
                  <span>PROTECTED ₹{outcome?.amount_withheld?.toLocaleString('en-IN') || '0'}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
