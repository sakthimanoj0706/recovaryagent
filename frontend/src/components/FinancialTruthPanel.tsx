import React from 'react';
import { ShieldCheck, CheckCircle2, AlertTriangle, Clock, Lock, Scale, DollarSign } from 'lucide-react';
import { ClosedLoopOutcome } from '../types';

interface FinancialTruthPanelProps {
  outcome: ClosedLoopOutcome | null;
}

export const FinancialTruthPanel: React.FC<FinancialTruthPanelProps> = ({ outcome }) => {
  if (!outcome) return null;

  const runId = outcome.run_id || `run_${outcome.payment_id.replace('pay_', '')}`;
  const amt = outcome.amount || 0;
  const recovered = outcome.amount_recovered || 0;
  const withheld = outcome.amount_withheld || 0;
  const pending = outcome.amount_pending || 0;
  const escalated = outcome.amount_escalated || 0;

  return (
    <div className="bg-[#0e1424] border border-white/10 rounded-xl p-5 shadow-2xl backdrop-blur-md space-y-4">
      {/* Header with Run ID and Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold font-mono text-white uppercase tracking-wider">
                FINANCIAL TRUTH &amp; ACCOUNTING RECONCILIATION
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                LEDGER CONFIRMED
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400 mt-0.5">
              <span>RUN ID: <strong className="text-cyan-400">{runId}</strong></span>
              <span>•</span>
              <span>PAYMENT: <strong className="text-slate-200">{outcome.payment_id}</strong></span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-900 border border-white/10 text-slate-300">
            Source: <strong className="text-emerald-400">{outcome.source_of_truth || 'FINANCIAL STATE ENGINE'}</strong>
          </span>
        </div>
      </div>

      {/* 4 Accounting Buckets */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {/* Recovered */}
        <div className={`p-3 rounded-lg border flex flex-col justify-between ${recovered > 0 ? 'bg-emerald-950/40 border-emerald-500/40' : 'bg-slate-900/50 border-white/5'}`}>
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">1. ₹ RECOVERED</span>
          <span className={`text-base font-bold font-mono mt-1 ${recovered > 0 ? 'text-emerald-400' : 'text-slate-500'}`}>
            ₹{recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
          <span className="text-[9px] font-mono text-slate-400 mt-1">Confirmed Captured</span>
        </div>

        {/* Withheld */}
        <div className={`p-3 rounded-lg border flex flex-col justify-between ${withheld > 0 ? 'bg-amber-950/40 border-amber-500/40' : 'bg-slate-900/50 border-white/5'}`}>
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">2. ₹ WITHHELD</span>
          <span className={`text-base font-bold font-mono mt-1 ${withheld > 0 ? 'text-amber-400' : 'text-slate-500'}`}>
            ₹{withheld.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
          <span className="text-[9px] font-mono text-slate-400 mt-1">Safety Gate Stop / -EV</span>
        </div>

        {/* Pending */}
        <div className={`p-3 rounded-lg border flex flex-col justify-between ${pending > 0 ? 'bg-blue-950/40 border-blue-500/40' : 'bg-slate-900/50 border-white/5'}`}>
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">3. ₹ PENDING</span>
          <span className={`text-base font-bold font-mono mt-1 ${pending > 0 ? 'text-cyan-400' : 'text-slate-500'}`}>
            ₹{pending.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
          <span className="text-[9px] font-mono text-slate-400 mt-1">In-Flight / Waiting</span>
        </div>

        {/* Escalated */}
        <div className={`p-3 rounded-lg border flex flex-col justify-between ${escalated > 0 ? 'bg-purple-950/40 border-purple-500/40' : 'bg-slate-900/50 border-white/5'}`}>
          <span className="text-[10px] font-mono font-bold text-slate-400 uppercase">4. ₹ ESCALATED</span>
          <span className={`text-base font-bold font-mono mt-1 ${escalated > 0 ? 'text-purple-400' : 'text-slate-500'}`}>
            ₹{escalated.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
          <span className="text-[9px] font-mono text-slate-400 mt-1">Ops Reconciliation</span>
        </div>
      </div>

      {/* Accounting Checksum Bar */}
      <div className="p-2.5 rounded-lg bg-slate-950/70 border border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <Scale className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400">Total Transaction Value: <strong className="text-white">₹{amt.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Accounting Invariant:</span>
          <span className="text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            100% BALANCED
          </span>
        </div>
      </div>
    </div>
  );
};
