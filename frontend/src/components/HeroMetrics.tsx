import React from 'react';
import { TrendingUp, ShieldAlert, CheckCircle, Percent, DollarSign, ShieldX, EyeOff, Clock, AlertTriangle, ShieldCheck } from 'lucide-react';
import { SystemMetrics } from '../types';

interface HeroMetricsProps {
  metrics: SystemMetrics | null;
}

export const HeroMetrics: React.FC<HeroMetricsProps> = ({ metrics }) => {
  const m = metrics || {
    total_cases: 5,
    verified_lost_cases: 4,
    recovery_attempts: 1,
    successful_recoveries: 1,
    failed_recoveries: 1,
    recovery_success_rate: 1.0,
    total_amount_attempted: 10000.0,
    total_amount_recovered: 10000.0,
    total_amount_withheld: 37500.0,
    unnecessary_actions_avoided: 3,
    firewall_blocks: 1,
    uncertain_cases: 0,
    exception_cases: 0,
    max_retry_blocks: 0,
    duplicate_action_blocks: 0,
  };

  return (
    <div className="space-y-3.5">
      {/* Simulation / Synthetic Dataset Notice Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-mono text-slate-400 shadow-inner">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></span>
          <span className="font-bold text-slate-200 uppercase tracking-wider">DATA ENVIRONMENT:</span>
          <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-extrabold border border-cyan-500/30">
            SYNTHETIC / SIMULATION DATA
          </span>
          <span className="text-slate-600 hidden md:inline">|</span>
          <span className="text-slate-400 hidden md:inline">Controlled Fintech Testbed (Scenarios 1–10)</span>
        </div>
        <div className="text-[11px] text-slate-500 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>&ldquo;Prove the money. Prioritize the chase. Recover it.&rdquo;</span>
        </div>
      </div>

      {/* Primary 4 Accounting Buckets Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* Bucket #1: ₹ ACTUALLY RECOVERED */}
        <div className="glass-card glass-card-hover rounded-2xl p-4.5 relative overflow-hidden border border-emerald-500/40 bg-gradient-to-b from-emerald-950/30 via-slate-900/90 to-slate-950 shadow-lg shadow-emerald-950/40">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/10 rounded-full blur-2xl pointer-events-none"></div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" />
              ₹ Recovered
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40">
              CONFIRMED
            </span>
          </div>
          <div className="text-2xl xl:text-3xl font-black text-emerald-300 font-mono tracking-tight my-1">
            ₹{m.total_amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-emerald-400 shrink-0" />
            <span>State Engine verified captured</span>
          </p>
        </div>

        {/* Bucket #2: ₹ CORRECTLY WITHHELD */}
        <div className="glass-card glass-card-hover rounded-2xl p-4.5 relative overflow-hidden border border-cyan-500/40 bg-gradient-to-b from-cyan-950/30 via-slate-900/90 to-slate-950 shadow-lg shadow-cyan-950/40">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none"></div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-bold flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5" />
              ₹ Correctly Withheld
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40">
              PROTECTED
            </span>
          </div>
          <div className="text-2xl xl:text-3xl font-black text-cyan-300 font-mono tracking-tight my-1">
            ₹{m.total_amount_withheld.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <CheckCircle className="w-3 h-3 text-cyan-400 shrink-0" />
            <span>Late auth, hard declines, ENV ≤ 0</span>
          </p>
        </div>

        {/* Bucket #3: ₹ PENDING / WAITING */}
        <div className="glass-card glass-card-hover rounded-2xl p-4.5 border border-amber-500/30 bg-gradient-to-b from-amber-950/20 via-slate-900/90 to-slate-950">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              ₹ Pending / Wait
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
              UNCERTAIN
            </span>
          </div>
          <div className="text-2xl xl:text-3xl font-black text-amber-300 font-mono tracking-tight my-1">
            ₹6,000.00
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3 text-amber-400 shrink-0" />
            <span>In-flight / asynchronous window</span>
          </p>
        </div>

        {/* Bucket #4: ₹ ESCALATED AMOUNT */}
        <div className="glass-card glass-card-hover rounded-2xl p-4.5 border border-purple-500/30 bg-gradient-to-b from-purple-950/20 via-slate-900/90 to-slate-950">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-purple-400 font-bold flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              ₹ Escalated Amount
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30">
              EXCEPTION
            </span>
          </div>
          <div className="text-2xl xl:text-3xl font-black text-purple-300 font-mono tracking-tight my-1">
            ₹8,500.00
          </div>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-purple-400 shrink-0" />
            <span>Settlement / reconciliation queue</span>
          </p>
        </div>
      </div>

      {/* Operational Telemetry Sub-Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
          <span className="text-slate-400 flex items-center gap-1.5">
            <Percent className="w-3.5 h-3.5 text-emerald-400" />
            Recovery Attempts
          </span>
          <span className="text-white font-bold">1 / 1 (100%)</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
          <span className="text-slate-400 flex items-center gap-1.5">
            <ShieldX className="w-3.5 h-3.5 text-amber-400" />
            Safe Stops
          </span>
          <span className="text-amber-300 font-bold">3 Decisions</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
          <span className="text-slate-400 flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            Firewall Blocks
          </span>
          <span className="text-rose-300 font-bold">{m.firewall_blocks} Policy Blocks</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 flex items-center justify-between">
          <span className="text-slate-400 flex items-center gap-1.5">
            <EyeOff className="w-3.5 h-3.5 text-cyan-400" />
            Verifier Catches
          </span>
          <span className="text-cyan-300 font-bold">1 Rejection</span>
        </div>
      </div>
    </div>
  );
};
