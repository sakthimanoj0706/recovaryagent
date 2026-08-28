import React from 'react';
import { Activity, Shield, Cpu, Lock, Radio, Database, CheckCircle2 } from 'lucide-react';

interface SubsystemInfo {
  status: string;
  mode?: string;
  provider?: string;
  is_simulation?: boolean;
}

interface SystemHealthData {
  timestamp: string;
  status: string;
  simulation_mode: boolean;
  subsystems: {
    ingestion: SubsystemInfo;
    state_engine: SubsystemInfo;
    agent: SubsystemInfo;
    firewall: SubsystemInfo;
    gateway: SubsystemInfo;
    verifier: SubsystemInfo;
    audit: SubsystemInfo;
  };
}

interface SystemHealthPanelProps {
  health?: SystemHealthData | null;
}

export const SystemHealthPanel: React.FC<SystemHealthPanelProps> = ({ health }) => {
  const subsystems = [
    {
      name: 'INGESTION',
      icon: <Radio className="w-4 h-4 text-cyan-400" />,
      status: health?.subsystems?.ingestion?.status || 'HEALTHY',
      badge: 'IDEMPOTENT STREAM',
      color: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    },
    {
      name: 'STATE ENGINE',
      icon: <Database className="w-4 h-4 text-emerald-400" />,
      status: health?.subsystems?.state_engine?.status || 'HEALTHY',
      badge: 'FINANCIAL TRUTH',
      color: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    },
    {
      name: 'AGENT',
      icon: <Cpu className="w-4 h-4 text-indigo-400" />,
      status: health?.subsystems?.agent?.status || 'HEALTHY',
      badge: 'BOUNDED ADVISORY',
      color: 'border-indigo-500/30 bg-indigo-500/10 text-indigo-300',
    },
    {
      name: 'FIREWALL',
      icon: <Lock className="w-4 h-4 text-amber-400" />,
      status: health?.subsystems?.firewall?.status || 'ACTIVE',
      badge: 'DETERMINISTIC GATES',
      color: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    },
    {
      name: 'GATEWAY',
      icon: <Activity className="w-4 h-4 text-purple-400" />,
      status: health?.subsystems?.gateway?.status || 'SIMULATION',
      badge: 'MOCK ADAPTER',
      color: 'border-purple-500/30 bg-purple-500/10 text-purple-300',
    },
    {
      name: 'VERIFIER',
      icon: <Shield className="w-4 h-4 text-emerald-400" />,
      status: health?.subsystems?.verifier?.status || 'HEALTHY',
      badge: 'LEDGER CONFIRMATION',
      color: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    },
    {
      name: 'AUDIT',
      icon: <CheckCircle2 className="w-4 h-4 text-blue-400" />,
      status: health?.subsystems?.audit?.status || 'APPEND-ONLY',
      badge: 'IMMUTABLE JSONL',
      color: 'border-blue-500/30 bg-blue-500/10 text-blue-300',
    },
  ];

  return (
    <div className="bg-[#0e1424] border border-white/10 rounded-xl p-4 shadow-lg backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-200">
            SYSTEM HEALTH & MODULE TOPOLOGY
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
            ALL SUBSYSTEMS OPERATIONAL
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold">
            SIMULATION MODE
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        {subsystems.map((sub, idx) => (
          <div
            key={idx}
            className="p-2.5 rounded-lg bg-slate-900/60 border border-white/5 flex flex-col justify-between hover:border-white/20 transition-colors"
          >
            <div className="flex items-center justify-between gap-1 mb-1.5">
              <span className="text-[10px] font-bold font-mono text-slate-300 flex items-center gap-1.5">
                {sub.icon}
                {sub.name}
              </span>
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            </div>
            <div className="flex flex-col gap-1">
              <span className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded text-center border ${sub.color}`}>
                ● {sub.status}
              </span>
              <span className="text-[9px] font-mono text-slate-400 text-center truncate">
                {sub.badge}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
