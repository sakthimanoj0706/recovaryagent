import React from 'react';
import { motion } from 'framer-motion';
import {
  CreditCard,
  SearchCheck,
  BarChart3,
  BrainCircuit,
  Scale,
  ShieldCheck,
  PlayCircle,
  CheckCircle2,
  FileSpreadsheet,
  XCircle,
  AlertTriangle,
  Sparkles,
  Lock,
} from 'lucide-react';
import { PipelineStep, ClosedLoopOutcome } from '../types';

interface LivePipelineProps {
  timeline: PipelineStep[];
  outcome: ClosedLoopOutcome | null;
  isRunning: boolean;
  activeStepIndex: number;
}

const STAGES = [
  { id: 'OBSERVE', label: '1. OBSERVE', desc: 'Ingestion & Timeline', icon: CreditCard },
  { id: 'PROVE', label: '2. PROVE', desc: 'Financial State Engine', icon: SearchCheck },
  { id: 'PRIORITIZE', label: '3. PRIORITIZE', desc: 'Economics & ML', icon: BarChart3 },
  { id: 'PLAN', label: '4. PLAN', desc: 'Advisory Planner', icon: BrainCircuit },
  { id: 'POLICY', label: '5. POLICY', desc: 'Action Validation', icon: Scale },
  { id: 'GUARD', label: '6. GUARD', desc: 'Recovery Firewall', icon: ShieldCheck },
  { id: 'ACT', label: '7. ACT', desc: 'Gateway Dispatch', icon: PlayCircle },
  { id: 'VERIFY', label: '8. VERIFY', desc: 'Independent Ledger', icon: CheckCircle2 },
  { id: 'AUDIT', label: '9. AUDIT', desc: 'Immutable JSONL', icon: FileSpreadsheet },
];

export const LivePipeline: React.FC<LivePipelineProps> = ({
  timeline,
  outcome,
  isRunning,
  activeStepIndex,
}) => {
  const runId = outcome?.run_id || 'run_active';

  return (
    <div className="bg-[#0e1424] rounded-2xl p-6 border border-white/10 relative overflow-hidden shadow-2xl space-y-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase tracking-wider">
              7-Stage Deterministic Safety
            </span>
            <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-emerald-400" />
              LIVE RECOVERY PIPELINE TRAJECTORY
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            OBSERVE → PROVE → PRIORITIZE → PLAN → POLICY → GUARD → ACT → VERIFY → AUDIT
          </p>
        </div>

        <div className="flex items-center gap-3">
          {outcome && (
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-900 border border-white/10 text-cyan-400">
              RUN: <strong>{runId}</strong>
            </span>
          )}

          {isRunning && (
            <div className="flex items-center gap-2 text-xs font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              <span>EXECUTING PIPELINE...</span>
            </div>
          )}
        </div>
      </div>

      {/* 9-Stage Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-9 gap-2 relative">
        {STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const isPassed = activeStepIndex > idx;
          const isCurrent = activeStepIndex === idx;
          const stepData = timeline.find((t) => t.step === stage.id || t.step === stage.label.split(' ')[1]);
          const isBlocked = stepData?.status === 'BLOCKED' || (outcome && outcome.firewall_decision === 'STOP' && idx >= 5);

          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
              className={`p-3 rounded-xl border flex flex-col justify-between transition-all relative min-h-[140px] ${
                isCurrent
                  ? 'bg-emerald-500/10 border-emerald-400 shadow-md shadow-emerald-950 ring-1 ring-emerald-400/50'
                  : isBlocked
                  ? 'bg-amber-950/20 border-amber-500/40 text-slate-400'
                  : isPassed
                  ? 'bg-slate-900/60 border-white/10 text-slate-300'
                  : 'bg-slate-950/40 border-white/5 opacity-60'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div
                    className={`p-1.5 rounded-lg ${
                      isCurrent
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : isBlocked
                        ? 'bg-amber-500/20 text-amber-300'
                        : isPassed
                        ? 'bg-white/10 text-white'
                        : 'bg-white/5 text-slate-500'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                  </div>

                  {isBlocked ? (
                    <Lock className="w-3.5 h-3.5 text-amber-400" />
                  ) : isPassed ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : isCurrent ? (
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                  ) : null}
                </div>

                <div className="font-mono text-[11px] font-bold text-white tracking-tight">{stage.label}</div>
                <div className="text-[10px] text-slate-400 mt-0.5 leading-tight">{stage.desc}</div>
              </div>

              {/* Status Message */}
              <div className="mt-2 pt-2 border-t border-white/5 text-[9px] font-mono">
                {stepData ? (
                  <div className="text-slate-300 truncate" title={stepData.message}>
                    {stepData.message}
                  </div>
                ) : isCurrent ? (
                  <span className="text-emerald-400 font-semibold animate-pulse">Evaluating...</span>
                ) : isPassed ? (
                  <span className="text-slate-400">Completed</span>
                ) : isBlocked ? (
                  <span className="text-amber-400 font-semibold">Firewall Stop</span>
                ) : (
                  <span className="text-slate-600">Pending</span>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
