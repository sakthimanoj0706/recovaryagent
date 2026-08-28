import React from 'react';
import { ShieldCheck, Activity, RefreshCw, Database, Terminal, RotateCcw, AlertTriangle, CheckCircle2 } from 'lucide-react';

interface HeaderProps {
  onRefresh: () => void;
  onOpenAudit: () => void;
  onResetDemo?: () => void;
  isLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, onOpenAudit, onResetDemo, isLoading }) => {
  return (
    <header className="border-b border-white/10 bg-[#0a0f1d]/90 backdrop-blur-md sticky top-0 z-40 px-4 sm:px-6 py-3.5 shadow-2xl">
      <div className="max-w-[1600px] mx-auto flex flex-col xl:flex-row xl:items-center justify-between gap-3">
        {/* Brand & Mission Statement */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-400 p-[1px] flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <div className="w-full h-full bg-[#080b11] rounded-[11px] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold tracking-wider text-white font-mono flex items-center gap-1">
                RECOVER<span className="text-emerald-400">AI</span>
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                Command Center
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping"></span>
                SIMULATION MODE | NO REAL TRANSACTIONS
              </span>
            </div>
            <p className="text-xs text-slate-300 font-mono mt-0.5">
              &ldquo;Prove the money. Prioritize the chase. Recover it.&rdquo;
            </p>
          </div>
        </div>

        {/* Global Controls & Status Badges */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Health Badge */}
          <div className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-emerald-500/30 text-emerald-400 font-bold">
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            <span>SYSTEM HEALTH: HEALTHY</span>
          </div>

          {/* Ledger Authority Badge */}
          <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900 border border-cyan-500/30 text-cyan-300 font-bold">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>FINANCIAL TRUTH: LEDGER AUTHORITATIVE</span>
          </div>

          {/* Reset Demo Button */}
          {onResetDemo && (
            <button
              onClick={onResetDemo}
              disabled={isLoading}
              title="Reset in-memory simulation state"
              className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all disabled:opacity-50 font-bold"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Demo</span>
            </button>
          )}

          {/* Audit Trail Button */}
          <button
            onClick={onOpenAudit}
            className="flex items-center gap-1.5 text-xs font-mono px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-white/10 transition-colors shadow-sm font-semibold"
          >
            <Database className="w-3.5 h-3.5 text-cyan-400" />
            <span>Audit Trail</span>
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs font-mono px-3.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-all disabled:opacity-50 font-semibold"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
        </div>
      </div>
    </header>
  );
};
