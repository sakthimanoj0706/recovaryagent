import React from 'react';
import { ShieldCheck, Activity, RefreshCw, Database, Terminal } from 'lucide-react';

interface HeaderProps {
  onRefresh: () => void;
  onOpenAudit: () => void;
  isLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, onOpenAudit, isLoading }) => {
  return (
    <header className="border-b border-white/10 bg-[#0a0f1d]/80 backdrop-blur-md sticky top-0 z-40 px-6 py-4">
      <div className="max-w-[1600px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Brand & Subtitle */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-cyan-400 p-[1px] flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <div className="w-full h-full bg-[#080b11] rounded-[11px] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-wider text-white font-mono flex items-center gap-2">
                RECOVER<span className="text-emerald-400">AI</span>
              </h1>
              <span className="text-xs px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                Command Center
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium tracking-wider bg-amber-500/10 text-amber-300 border border-amber-500/30 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                SIMULATION MODE
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              &ldquo;Prove the money. Prioritize the chase. Recover it.&rdquo;
            </p>
          </div>
        </div>

        {/* Global Controls & Status */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-slate-900/60 border border-white/5 text-slate-300">
            <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span>FINANCIAL ENGINE: ONLINE</span>
          </div>

          <button
            onClick={onOpenAudit}
            className="flex items-center gap-1.5 text-xs font-medium px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-white/10 transition-colors shadow-sm"
          >
            <Database className="w-3.5 h-3.5 text-cyan-400" />
            <span>Audit Trail</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs font-medium px-3.5 py-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>
    </header>
  );
};
