import React, { useState } from 'react';
import {
  Play,
  Sparkles,
  ShieldCheck,
  Ban,
  DollarSign,
  Search,
  CheckCircle,
  Clock,
  AlertTriangle,
  PlayCircle,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface ScenarioSimulatorProps {
  onRunScenario: (scenarioId: string, customAmount?: number) => void;
  isRunning: boolean;
}

interface ScenarioDef {
  id: string;
  category: string;
  categoryIcon: string;
  name: string;
  tag: string;
  amount: string;
  expected: string;
  badgeColor: string;
  borderHover: string;
  icon: React.ReactNode;
  summary: string;
}

const FIVE_SCENARIOS: ScenarioDef[] = [
  {
    id: 'case_a',
    category: 'SAFETY',
    categoryIcon: '🛡️',
    name: 'FAILED ≠ LOST',
    tag: 'LATE AUTH FLIP-FLOP',
    amount: '₹25,000',
    expected: '₹25,000 Withheld (Rule 006)',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
    borderHover: 'hover:border-cyan-500/50 hover:bg-cyan-950/20',
    icon: <ShieldCheck className="w-4 h-4 text-cyan-400" />,
    summary: 'Payment failed at T+0s, authorized at T+30s. Ledger re-evaluates to ALREADY_RECOVERED; Firewall blocks double-charge.',
  },
  {
    id: 'case_b',
    category: 'ECONOMICS',
    categoryIcon: '💰',
    name: 'ECONOMICS ≠ PERMISSION',
    tag: 'HARD DECLINE BLOCK',
    amount: '₹12,000',
    expected: '₹12,000 Protected (Rule 004)',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    borderHover: 'hover:border-amber-500/50 hover:bg-amber-950/20',
    icon: <Ban className="w-4 h-4 text-amber-400" />,
    summary: 'Positive ENV (+₹1,632) but card blocked. Deterministic Firewall overrides AI recommendation to prevent network fines.',
  },
  {
    id: 'case_c',
    category: 'AI TRUST',
    categoryIcon: '🤖',
    name: 'AGENT CLAIM ≠ TRUTH',
    tag: 'VERIFICATION CATCH',
    amount: '₹15,000',
    expected: 'Zero False Recovery (Ledger Catch)',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    borderHover: 'hover:border-rose-500/50 hover:bg-rose-950/20',
    icon: <Search className="w-4 h-4 text-rose-400" />,
    summary: 'Gateway claims link sent, customer abandons checkout. Verifier checks ledger and rejects optimistic AI claim.',
  },
  {
    id: 'case_d',
    category: 'CONSISTENCY',
    categoryIcon: '⏳',
    name: 'UNCERTAIN → WAIT',
    tag: 'IN-FLIGHT PENDING',
    amount: '₹6,000',
    expected: '₹6,000 Held in Pending',
    badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    borderHover: 'hover:border-blue-500/50 hover:bg-blue-950/20',
    icon: <Clock className="w-4 h-4 text-blue-400" />,
    summary: 'Payment pending in bank clearing window. Agent waits safely instead of triggering redundant recovery.',
  },
  {
    id: 'case_e',
    category: 'EXCEPTION',
    categoryIcon: '🚨',
    name: 'EXCEPTION → ESCALATE',
    tag: 'SETTLEMENT MISMATCH',
    amount: '₹8,500',
    expected: '₹8,500 Escalated to Ops',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/40',
    borderHover: 'hover:border-purple-500/50 hover:bg-purple-950/20',
    icon: <AlertTriangle className="w-4 h-4 text-purple-400" />,
    summary: '₹8,000 settled for an ₹8,500 order. State Engine detects discrepancy and routes directly to human operations.',
  },
];

export const ScenarioSimulator: React.FC<ScenarioSimulatorProps> = ({ onRunScenario, isRunning }) => {
  const [selectedId, setSelectedId] = useState<string>('case_a');

  const handleRunAll = async () => {
    for (const sc of FIVE_SCENARIOS) {
      onRunScenario(sc.id);
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
  };

  return (
    <div className="bg-[#0e1424] rounded-2xl p-5 sm:p-6 border border-white/10 relative overflow-hidden shadow-2xl space-y-4">
      {/* Top Header & Global Triggers */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase tracking-wider">
              Judge-Ready Demonstrations
            </span>
            <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              FINTECH SCENARIO COMMAND CENTER
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Select any fintech archetype to execute the complete live closed-loop pipeline and prove financial truth isolation.
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => onRunScenario('1')}
            disabled={isRunning}
            className="flex items-center gap-1.5 text-xs font-mono px-3.5 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-extrabold shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>LIVE DEMO</span>
          </button>

          <button
            onClick={handleRunAll}
            disabled={isRunning}
            className="flex items-center gap-1.5 text-xs font-mono px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-white/10 font-bold transition-all disabled:opacity-50"
          >
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>RUN ALL 5</span>
          </button>
        </div>
      </div>

      {/* 5 Scenario Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {FIVE_SCENARIOS.map((s) => {
          const isSelected = selectedId === s.id;

          return (
            <div
              key={s.id}
              onClick={() => {
                setSelectedId(s.id);
                onRunScenario(s.id);
              }}
              className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all flex flex-col justify-between space-y-2 relative overflow-hidden group ${
                isSelected
                  ? 'bg-slate-900 border-cyan-400/80 shadow-md ring-1 ring-cyan-400/40'
                  : 'bg-slate-950/60 border-white/5 hover:border-white/20'
              } ${s.borderHover}`}
            >
              {/* Category & Tag */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-mono font-bold text-slate-400 flex items-center gap-1">
                    <span>{s.categoryIcon}</span>
                    <span>{s.category}</span>
                  </span>
                  <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-bold uppercase border ${s.badgeColor}`}>
                    {s.tag}
                  </span>
                </div>

                <h4 className="text-xs font-bold text-white font-mono">{s.name}</h4>
                <div className="text-sm font-extrabold text-cyan-400 font-mono mt-0.5">{s.amount}</div>
              </div>

              {/* Summary Description */}
              <p className="text-[10px] text-slate-400 leading-relaxed font-sans line-clamp-3">
                {s.summary}
              </p>

              {/* Expected Result & Run Trigger */}
              <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[10px] font-mono">
                <span className="text-slate-300 font-semibold">{s.expected}</span>
                <span className="text-cyan-400 group-hover:translate-x-1 transition-transform">
                  <Play className="w-3 h-3 fill-current" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
