import React from 'react';
import { motion } from 'framer-motion';
import { 
  CreditCard, 
  SearchCheck, 
  BarChart3, 
  BrainCircuit, 
  ShieldCheck, 
  PlayCircle, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { PipelineStep, ClosedLoopOutcome } from '../types';

interface LivePipelineProps {
  timeline: PipelineStep[];
  outcome: ClosedLoopOutcome | null;
  isRunning: boolean;
  activeStepIndex: number;
}

const STAGES = [
  { id: 'PAYMENT', label: '1. PAYMENT', desc: 'Raw Ingestion', icon: CreditCard },
  { id: 'PROVE', label: '2. PROVE', desc: 'State Engine', icon: SearchCheck },
  { id: 'PRIORITIZE', label: '3. PRIORITIZE', desc: 'Economics & ML', icon: BarChart3 },
  { id: 'AGENT', label: '4. AGENT', desc: 'Advisory Planner', icon: BrainCircuit },
  { id: 'FIREWALL', label: '5. FIREWALL', desc: 'Safety Rules', icon: ShieldCheck },
  { id: 'ACT', label: '6. ACT', desc: 'Simulated Dispatch', icon: PlayCircle },
  { id: 'VERIFY', label: '7. VERIFY', desc: 'Closed Loop Truth', icon: CheckCircle2 },
];

export const LivePipeline: React.FC<LivePipelineProps> = ({
  timeline,
  outcome,
  isRunning,
  activeStepIndex,
}) => {
  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-6">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2 font-mono">
            <Sparkles className="w-4 h-4 text-emerald-400" />
            LIVE RECOVERY PIPELINE
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time closed-loop decision trajectory (PROVE → PRIORITIZE → ACT → VERIFY)
          </p>
        </div>

        {isRunning && (
          <div className="flex items-center gap-2 text-xs font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span>EXECUTING PIPELINE...</span>
          </div>
        )}
      </div>

      {/* Interactive Stage Tracker */}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-3 relative">
        {STAGES.map((stage, idx) => {
          const Icon = stage.icon;
          const isPassed = activeStepIndex > idx;
          const isCurrent = activeStepIndex === idx;
          const stepData = timeline.find((t) => t.step === stage.id);
          const isBlocked = stepData?.status === 'BLOCKED' || (outcome && outcome.firewall_decision === 'STOP' && idx >= 4);

          let borderStyle = 'border-white/5 bg-slate-900/40 text-slate-500';
          let iconColor = 'text-slate-500';
          let glow = '';

          if (isCurrent) {
            borderStyle = 'border-cyan-400 bg-cyan-950/40 text-cyan-200 shadow-lg shadow-cyan-900/40';
            iconColor = 'text-cyan-300 animate-bounce';
            glow = 'ring-2 ring-cyan-400/50';
          } else if (isPassed) {
            if (isBlocked) {
              borderStyle = 'border-amber-500/40 bg-amber-950/20 text-amber-300';
              iconColor = 'text-amber-400';
            } else {
              borderStyle = 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300';
              iconColor = 'text-emerald-400';
            }
          }

          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              className={`relative rounded-xl p-3.5 border transition-all duration-300 flex flex-col justify-between min-h-[110px] ${borderStyle} ${glow}`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono font-bold tracking-wider uppercase opacity-80">
                    {stage.label}
                  </span>
                  <Icon className={`w-4 h-4 ${iconColor}`} />
                </div>
                <div className="text-xs font-medium text-slate-300 font-sans line-clamp-1">
                  {stage.desc}
                </div>
              </div>

              <div className="mt-2 text-[10px] font-mono">
                {isCurrent && isRunning ? (
                  <span className="text-cyan-400 animate-pulse font-semibold">Analyzing...</span>
                ) : isPassed && stepData ? (
                  <span className={stepData.status === 'BLOCKED' ? 'text-amber-400' : 'text-emerald-400 font-semibold'}>
                    {stepData.status}
                  </span>
                ) : (
                  <span className="text-slate-600">Pending</span>
                )}
              </div>

              {/* Connecting Arrow for desktop */}
              {idx < STAGES.length - 1 && (
                <div className="hidden md:block absolute -right-2 top-1/2 -translate-y-1/2 z-10 text-slate-700 pointer-events-none">
                  <ArrowRight className="w-3 h-3 text-slate-600" />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Real-time Summary Card below stages */}
      {outcome && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mt-5 p-4 rounded-xl border font-mono text-xs flex flex-col md:flex-row md:items-center justify-between gap-3 ${
            outcome.final_outcome === 'RECOVERY_SUCCESS'
              ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
              : outcome.final_outcome === 'RECOVERY_FAILED'
              ? 'bg-rose-950/30 border-rose-500/40 text-rose-300'
              : 'bg-cyan-950/30 border-cyan-500/40 text-cyan-300'
          }`}
        >
          <div className="flex items-center gap-3">
            {outcome.final_outcome === 'RECOVERY_SUCCESS' ? (
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              </div>
            ) : outcome.final_outcome === 'RECOVERY_FAILED' ? (
              <div className="w-8 h-8 rounded-lg bg-rose-500/20 flex items-center justify-center shrink-0">
                <XCircle className="w-5 h-5 text-rose-400" />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-5 h-5 text-cyan-400" />
              </div>
            )}
            <div>
              <div className="font-bold text-sm text-white">
                {outcome.final_outcome === 'RECOVERY_SUCCESS'
                  ? `✓ RECOVERY CONFIRMED: ₹${outcome.amount_recovered.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                  : outcome.final_outcome === 'RECOVERY_FAILED'
                  ? `✗ RECOVERY FAILED: Payment remains unrecovered`
                  : `🛑 ACTION BLOCKED: ₹${outcome.amount_withheld.toLocaleString('en-IN', { minimumFractionDigits: 2 })} CORRECTLY WITHHELD`}
              </div>
              <div className="text-slate-300 text-xs mt-0.5">{outcome.reason}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 text-right shrink-0">
            <div className="text-[11px] px-3 py-1 rounded bg-black/40 border border-white/10 text-slate-300">
              Source of Truth: <span className="text-white font-bold">{outcome.source_of_truth}</span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};
