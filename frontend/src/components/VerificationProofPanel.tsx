import React from 'react';
import { ShieldCheck, ArrowRight, CheckCircle2, XCircle, AlertCircle, Scale, ShieldAlert } from 'lucide-react';
import { ClosedLoopOutcome } from '../types';

interface VerificationProofPanelProps {
  outcome: ClosedLoopOutcome | null;
}

export const VerificationProofPanel: React.FC<VerificationProofPanelProps> = ({ outcome }) => {
  if (!outcome) return null;

  const isSuccess = outcome.final_outcome === 'RECOVERY_SUCCESS';
  const isFailed = outcome.final_outcome === 'RECOVERY_FAILED';
  const isWithheld = !isSuccess && !isFailed;

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-5 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2 font-mono">
            <Scale className="w-4 h-4 text-emerald-400" />
            CLOSED-LOOP VERIFICATION PROOF
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Decoupled verification: The Financial State Engine is the sole financial authority
          </p>
        </div>
        <div className="text-[11px] font-mono px-3 py-1 rounded bg-slate-900 border border-white/10 text-amber-300 flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
          <span>Agent Claim ≠ Financial Truth</span>
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
        {/* Step 1: Agent Claim */}
        <div className="p-4 rounded-xl bg-slate-900/50 border border-white/5 flex flex-col justify-between min-h-[140px]">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 font-semibold mb-1">
              Step 1: Agent & Executor Action
            </div>
            <div className="text-sm font-bold text-white font-mono">
              {outcome.agent_action || 'STOP'}
            </div>
            <div className="text-xs text-slate-400 mt-2">
              Status: <span className="text-slate-200 font-mono">{outcome.execution_status}</span>
            </div>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 font-mono">
            Claimed: {outcome.execution_status === 'SIMULATED_SUCCESS' ? 'Dispatched' : 'Halted / Failed'}
          </div>
        </div>

        {/* Step 2: Verification Engine */}
        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex flex-col justify-between min-h-[140px]">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold mb-1 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              Step 2: Independent State Verification
            </div>
            <div className="text-sm font-bold text-emerald-300 font-mono">
              {outcome.verification_state}
            </div>
            <div className="text-xs text-slate-300 mt-2">
              Re-evaluated full ledger history & subsequent capture events.
            </div>
          </div>
          <div className="mt-3 text-[11px] text-emerald-400 font-mono">
            Authority: Financial State Engine
          </div>
        </div>

        {/* Step 3: Verified Financial Result */}
        <div className={`p-4 rounded-xl border flex flex-col justify-between min-h-[140px] ${
          isSuccess ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-200' :
          isFailed ? 'bg-rose-950/40 border-rose-500/50 text-rose-200' :
          'bg-cyan-950/40 border-cyan-500/50 text-cyan-200'
        }`}>
          <div>
            <div className="text-[10px] font-mono uppercase tracking-wider font-semibold mb-1">
              Step 3: Final Verified Verdict
            </div>
            <div className="text-base font-extrabold font-mono flex items-center gap-1.5">
              {isSuccess ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>RECOVERY SUCCESS</span>
                </>
              ) : isFailed ? (
                <>
                  <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>RECOVERY FAILED</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span>{outcome.final_outcome}</span>
                </>
              )}
            </div>
            <div className="text-xs text-slate-200 mt-2">
              {isSuccess
                ? `₹${outcome.amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })} credited to merchant.`
                : isWithheld
                ? `₹${outcome.amount_withheld.toLocaleString('en-IN', { minimumFractionDigits: 2 })} correctly withheld.`
                : 'No funds captured. Zero false recovery claims.'}
            </div>
          </div>
          <div className="mt-3 text-[11px] font-mono opacity-80">
            {isSuccess ? 'Hero Metric #1 Updated' : isWithheld ? 'Safety Hero #2 Updated' : 'Safe Audit Logged'}
          </div>
        </div>
      </div>
    </div>
  );
};
