import React from 'react';
import {
  TrendingUp,
  ShieldCheck,
  Percent,
  Lock,
  Clock,
  AlertTriangle,
  Scale,
  RotateCcw,
  CheckCircle2,
  AlertOctagon,
  FileCheck2,
} from 'lucide-react';
import { SystemMetrics } from '../types';

interface HeroMetricsProps {
  metrics: SystemMetrics | null;
}

export const HeroMetrics: React.FC<HeroMetricsProps> = ({ metrics }) => {
  const m = metrics || {
    total_cases: 0,
    verified_lost_cases: 0,
    recovery_attempts: 0,
    successful_recoveries: 0,
    failed_recoveries: 0,
    recovery_success_rate: 0.0,
    total_amount_attempted: 0.0,
    total_amount_recovered: 0.0,
    total_amount_withheld: 0.0,
    total_amount_pending: 0.0,
    total_amount_escalated: 0.0,
    unnecessary_actions_avoided: 0,
    firewall_blocks: 0,
    safe_stops: 0,
    verification_catches: 0,
    uncertain_cases: 0,
    exception_cases: 0,
    escalations: 0,
    max_retry_blocks: 0,
    duplicate_action_blocks: 0,
  };

  const recovered = m.total_amount_recovered || 0;
  const withheld = m.total_amount_withheld || 0;
  const pending = (m as any).total_amount_pending || 0;
  const escalated = (m as any).total_amount_escalated || 0;
  const safeStops = (m as any).safe_stops || m.firewall_blocks || 0;
  const verCatches = (m as any).verification_catches || m.unnecessary_actions_avoided || 0;

  return (
    <div className="space-y-3.5">
      {/* Simulation / Executive Notice Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 px-4 py-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs font-mono text-slate-300 shadow-inner">
        <div className="flex flex-wrap items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping"></span>
          <span className="font-bold text-slate-100 uppercase tracking-wider">ENVIRONMENT:</span>
          <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 font-extrabold border border-cyan-500/30">
            SIMULATION / SANDBOX ONLY
          </span>
          <span className="text-slate-600 hidden md:inline">|</span>
          <span className="text-slate-400 hidden md:inline">Deterministic Safety &amp; Financial Ledger Authority</span>
        </div>
        <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>&ldquo;Prove the money. Prioritize the chase. Recover it.&rdquo;</span>
        </div>
      </div>

      {/* Row 1: Primary 4 Money Accounting Buckets */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {/* 1. ₹ ACTUALLY RECOVERED */}
        <div className="bg-[#0e1424] rounded-2xl p-4.5 relative overflow-hidden border border-emerald-500/40 bg-gradient-to-b from-emerald-950/30 via-slate-900/90 to-slate-950 shadow-lg shadow-emerald-950/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5" />
              ₹ ACTUALLY RECOVERED
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40">
              LEDGER VERIFIED
            </span>
          </div>
          <div className="text-2xl font-extrabold text-emerald-400 font-mono tracking-tight">
            ₹{recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-mono flex items-center justify-between">
            <span>Confirmed Settlement</span>
            <span className="text-emerald-300 font-semibold">{m.successful_recoveries} successful</span>
          </div>
        </div>

        {/* 2. ₹ CORRECTLY WITHHELD */}
        <div className="bg-[#0e1424] rounded-2xl p-4.5 relative overflow-hidden border border-amber-500/40 bg-gradient-to-b from-amber-950/30 via-slate-900/90 to-slate-950 shadow-lg shadow-amber-950/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-amber-400 font-bold flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              ₹ CORRECTLY WITHHELD
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40">
              SAFETY PROTECTED
            </span>
          </div>
          <div className="text-2xl font-extrabold text-amber-400 font-mono tracking-tight">
            ₹{withheld.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-mono flex items-center justify-between">
            <span>Flip-Flops / -EV / Hard Block</span>
            <span className="text-amber-300 font-semibold">Zero Double Charge</span>
          </div>
        </div>

        {/* 3. ₹ PENDING */}
        <div className="bg-[#0e1424] rounded-2xl p-4.5 relative overflow-hidden border border-blue-500/40 bg-gradient-to-b from-blue-950/30 via-slate-900/90 to-slate-950 shadow-lg shadow-blue-950/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-cyan-400 font-bold flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              ₹ PENDING
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 font-bold border border-blue-500/40">
              IN-FLIGHT
            </span>
          </div>
          <div className="text-2xl font-extrabold text-cyan-400 font-mono tracking-tight">
            ₹{pending.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-mono flex items-center justify-between">
            <span>Bank Clearing Window</span>
            <span className="text-cyan-300 font-semibold">{m.uncertain_cases} awaiting</span>
          </div>
        </div>

        {/* 4. ₹ ESCALATED */}
        <div className="bg-[#0e1424] rounded-2xl p-4.5 relative overflow-hidden border border-purple-500/40 bg-gradient-to-b from-purple-950/30 via-slate-900/90 to-slate-950 shadow-lg shadow-purple-950/40">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-mono uppercase tracking-wider text-purple-400 font-bold flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              ₹ ESCALATED
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 font-bold border border-purple-500/40">
              OPS REVIEW
            </span>
          </div>
          <div className="text-2xl font-extrabold text-purple-400 font-mono tracking-tight">
            ₹{escalated.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 font-mono flex items-center justify-between">
            <span>Settlement Discrepancies</span>
            <span className="text-purple-300 font-semibold">{m.exception_cases} cases</span>
          </div>
        </div>
      </div>

      {/* Row 2: Secondary Operational KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Recovery Attempts */}
        <div className="p-3.5 rounded-xl bg-slate-900/70 border border-white/5 flex items-center justify-between font-mono">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">RECOVERY ATTEMPTS</div>
            <div className="text-lg font-bold text-white mt-0.5">{m.recovery_attempts}</div>
            <div className="text-[9px] text-slate-500">Total attempted: ₹{m.total_amount_attempted.toLocaleString('en-IN')}</div>
          </div>
          <div className="p-2 rounded-lg bg-white/5 text-slate-400">
            <Percent className="w-4 h-4 text-cyan-400" />
          </div>
        </div>

        {/* Safe Stops */}
        <div className="p-3.5 rounded-xl bg-slate-900/70 border border-white/5 flex items-center justify-between font-mono">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SAFE STOPS (FIREWALL)</div>
            <div className="text-lg font-bold text-amber-300 mt-0.5">{safeStops}</div>
            <div className="text-[9px] text-slate-500">Hard declines &amp; max retries blocked</div>
          </div>
          <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400">
            <Lock className="w-4 h-4" />
          </div>
        </div>

        {/* Verification Catches */}
        <div className="p-3.5 rounded-xl bg-slate-900/70 border border-white/5 flex items-center justify-between font-mono">
          <div>
            <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">VERIFICATION CATCHES</div>
            <div className="text-lg font-bold text-emerald-300 mt-0.5">{verCatches}</div>
            <div className="text-[9px] text-slate-500">Prevented optimistic AI false success</div>
          </div>
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <FileCheck2 className="w-4 h-4" />
          </div>
        </div>
      </div>
    </div>
  );
};
