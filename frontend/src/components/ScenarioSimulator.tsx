import React from 'react';
import { Play, Sparkles, Sliders, ShieldCheck, ShieldAlert, Ban, DollarSign, Search, CheckCircle } from 'lucide-react';

interface ScenarioSimulatorProps {
  onRunScenario: (scenarioId: string, customAmount?: number) => void;
  isRunning: boolean;
}

interface ScenarioDef {
  id: string;
  num: string;
  name: string;
  tag: string;
  amount: string;
  expected: string;
  badgeColor: string;
  borderHover: string;
  icon: React.ReactNode;
}

const FIVE_SCENARIOS: ScenarioDef[] = [
  {
    id: '1',
    num: 'SCENARIO 1',
    name: 'Normal Successful Recovery',
    tag: 'SUCCESS PATH',
    amount: '₹10,000',
    expected: '₹10,000 Recovered',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    borderHover: 'hover:border-emerald-500/50 hover:bg-emerald-950/20',
    icon: <CheckCircle className="w-4 h-4 text-emerald-400" />,
  },
  {
    id: '2',
    num: 'SCENARIO 2',
    name: 'Failed ≠ Lost Flip-Flop',
    tag: 'HERO SAFETY #1',
    amount: '₹25,000',
    expected: '₹25,000 Withheld (Late Auth)',
    badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40',
    borderHover: 'hover:border-cyan-500/50 hover:bg-cyan-950/20',
    icon: <ShieldCheck className="w-4 h-4 text-cyan-400" />,
  },
  {
    id: '3',
    num: 'SCENARIO 3',
    name: 'Positive ENV + Hard Decline Block',
    tag: 'HERO SAFETY #2',
    amount: '₹12,000',
    expected: '₹12,000 Withheld (Rule 004)',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    borderHover: 'hover:border-amber-500/50 hover:bg-amber-950/20',
    icon: <Ban className="w-4 h-4 text-amber-400" />,
  },
  {
    id: '4',
    num: 'SCENARIO 4',
    name: 'Negative Unit Economics (ENV ≤ 0)',
    tag: 'UNIT ECONOMICS',
    amount: '₹500',
    expected: '₹500 Withheld (Gate Block)',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
    borderHover: 'hover:border-indigo-500/50 hover:bg-indigo-950/20',
    icon: <DollarSign className="w-4 h-4 text-indigo-400" />,
  },
  {
    id: '5',
    num: 'SCENARIO 5',
    name: 'Agent Claim ≠ Financial Truth',
    tag: 'VERIFIER PROOF',
    amount: '₹15,000',
    expected: 'RECOVERY_FAILED (₹0 False Win)',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    borderHover: 'hover:border-rose-500/50 hover:bg-rose-950/20',
    icon: <Search className="w-4 h-4 text-rose-400" />,
  },
];

export const ScenarioSimulator: React.FC<ScenarioSimulatorProps> = ({ onRunScenario, isRunning }) => {
  return (
    <div className="glass-card rounded-2xl p-5 sm:p-6 border border-white/10 relative overflow-hidden space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-3">
        <div>
          <h2 className="text-sm font-bold text-white flex items-center gap-2 font-mono">
            <Sliders className="w-4 h-4 text-emerald-400" />
            LIVE END-TO-END SCENARIO RUNNER
          </h2>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Click any scenario to execute live through the real Python backend pipeline.
          </p>
        </div>
        <div className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-white/5">
          5 Core Demo Scenarios
        </div>
      </div>

      {/* 5 Scenario Trigger Buttons Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {FIVE_SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => onRunScenario(s.id)}
            disabled={isRunning}
            className={`p-3 rounded-xl bg-slate-900/80 border border-white/10 ${s.borderHover} transition-all text-left flex flex-col justify-between group disabled:opacity-50 relative overflow-hidden`}
          >
            <div>
              <div className="flex items-center justify-between gap-1 mb-1.5">
                <span className="text-[10px] font-mono font-bold text-slate-400">
                  {s.num}
                </span>
                <span className={`text-[8px] font-mono px-1.5 py-0.2 rounded border font-bold ${s.badgeColor}`}>
                  {s.tag}
                </span>
              </div>
              <div className="text-xs font-bold text-white font-mono group-hover:text-emerald-300 transition-colors line-clamp-1">
                {s.name}
              </div>
              <div className="text-[11px] text-slate-400 font-mono mt-1">
                Amount: <span className="text-white font-semibold">{s.amount}</span>
              </div>
            </div>

            <div className="mt-3 pt-2 border-t border-white/5 flex items-center justify-between">
              <span className="text-[10px] text-slate-400 font-mono">
                {s.expected}
              </span>
              <div className="w-6 h-6 rounded-lg bg-emerald-500/20 group-hover:bg-emerald-500 flex items-center justify-center transition-all">
                <Play className="w-3 h-3 text-emerald-300 group-hover:text-slate-950 fill-current" />
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
};
