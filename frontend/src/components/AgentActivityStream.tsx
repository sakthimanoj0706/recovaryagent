import React from 'react';
import { Terminal, Clock, Cpu, CheckCircle2, Shield, Activity } from 'lucide-react';
import { ClosedLoopOutcome } from '../types';

interface AgentActivityStreamProps {
  outcome: ClosedLoopOutcome | null;
}

export const AgentActivityStream: React.FC<AgentActivityStreamProps> = ({ outcome }) => {
  const getLogs = () => {
    if (!outcome) {
      return [
        { time: '10:00:00', source: 'STATE ENGINE', text: 'System standing by. Awaiting payment lifecycle evaluation.' },
        { time: '10:00:01', source: 'FIREWALL', text: 'Rules 001 - 010 loaded and initialized.' },
        { time: '10:00:02', source: 'VERIFIER', text: 'Ledger audit hooks ready.' },
      ];
    }

    const now = new Date().toLocaleTimeString();
    const probStr = outcome.recovery_probability ? `${Math.round(outcome.recovery_probability * 100)}%` : 'N/A';
    const envStr = outcome.expected_net_value !== undefined ? `₹${outcome.expected_net_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}` : 'N/A';

    return [
      { time: now, source: 'STATE ENGINE', text: `Payment evaluated as ${outcome.initial_state}. (Proof verified via event sequence).` },
      { time: now, source: 'RECOVERY MODEL', text: `ML model predicted recovery probability: ${probStr}.` },
      { time: now, source: 'ECONOMIC ENGINE', text: `Calculated Expected Net Value: ${envStr}.` },
      { time: now, source: 'AGENT PLANNER', text: `Proposed action: ${outcome.agent_action || 'STOP'}. Confidence: ${(outcome.confidence * 100).toFixed(0)}%.` },
      { time: now, source: 'FIREWALL', text: `Firewall verdict: ${outcome.firewall_decision} ${outcome.firewall_rule ? `(${outcome.firewall_rule})` : ''}.` },
      { time: now, source: 'EXECUTOR', text: `Simulated dispatch: ${outcome.execution_status}.` },
      { time: now, source: 'VERIFIER', text: `Post-action financial re-check: ${outcome.verification_state} (Authority: ${outcome.source_of_truth}).` },
      { 
        time: now, 
        source: 'FINAL VERDICT', 
        text: outcome.final_outcome === 'RECOVERY_SUCCESS'
          ? `✓ ₹${outcome.amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })} successfully recovered.`
          : outcome.final_outcome === 'RECOVERY_FAILED'
          ? `✗ Action finished, but payment remains unrecovered.`
          : `🛑 Action halted. ₹${outcome.amount_withheld.toLocaleString('en-IN', { minimumFractionDigits: 2 })} correctly withheld.`
      },
    ];
  };

  const logs = getLogs();

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 relative overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-white font-mono uppercase tracking-wider">
            Agent Structured Telemetry
          </h3>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          EVENT STREAM
        </span>
      </div>

      <div className="space-y-2.5 font-mono text-xs overflow-y-auto max-h-[320px] pr-1">
        {logs.map((log, idx) => (
          <div key={idx} className="p-2.5 rounded-lg bg-black/40 border border-white/5 flex items-start gap-2.5">
            <span className="text-slate-500 text-[10px] shrink-0 mt-0.5">{log.time}</span>
            <div>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded mr-2 uppercase ${
                log.source === 'STATE ENGINE' ? 'bg-indigo-500/20 text-indigo-300' :
                log.source === 'FIREWALL' ? 'bg-amber-500/20 text-amber-300' :
                log.source === 'VERIFIER' || log.source === 'FINAL VERDICT' ? 'bg-emerald-500/20 text-emerald-300' :
                'bg-cyan-500/20 text-cyan-300'
              }`}>
                {log.source}
              </span>
              <span className="text-slate-200">{log.text}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
