import React, { useEffect, useState } from 'react';
import {
  X,
  ShieldCheck,
  DollarSign,
  Brain,
  Lock,
  CheckCircle2,
  AlertCircle,
  Play,
  Clock,
  RefreshCw,
  Sparkles,
  Zap,
} from 'lucide-react';
import { fetchPaymentDetails, fetchRecoveryTrace } from '../api';
import { AgentDecisionTrace } from '../types';

interface PaymentDetailPanelProps {
  paymentId?: string;
  onClose: () => void;
  onRunRecovery: (paymentId: string) => void;
  isRunning: boolean;
}

export const PaymentDetailPanel: React.FC<PaymentDetailPanelProps> = ({
  paymentId,
  onClose,
  onRunRecovery,
  isRunning,
}) => {
  const [details, setDetails] = useState<any>(null);
  const [trace, setTrace] = useState<AgentDecisionTrace | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!paymentId) {
      setDetails(null);
      setTrace(null);
      return;
    }

    let isMounted = true;
    setLoading(true);

    Promise.all([
      fetchPaymentDetails(paymentId).catch(() => null),
      fetchRecoveryTrace(paymentId).catch(() => null),
    ])
      .then(([detData, traceData]) => {
        if (isMounted) {
          setDetails(detData);
          setTrace(traceData);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch payment details & trace', err);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [paymentId]);

  if (!paymentId) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-[#090d18] border-l border-white/10 shadow-2xl p-6 overflow-y-auto font-mono text-xs flex flex-col justify-between">
      <div>
        {/* Top Header */}
        <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-5">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse"></span>
            <h3 className="text-sm font-bold text-white tracking-wider">
              FINANCIAL TRUTH &amp; DECISION AUDIT
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center text-slate-400 space-y-3">
            <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
            <span className="font-sans">Loading financial ledger &amp; decision trace...</span>
          </div>
        ) : details ? (
          <div className="space-y-4">
            {/* Payment Overview */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Payment ID</span>
                <span className="text-white font-bold">{details.payment?.payment_id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Order ID</span>
                <span className="text-slate-300">{details.payment?.order_id || 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Amount</span>
                <span className="text-emerald-300 font-extrabold text-sm">
                  ₹{Number(details.payment?.amount || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-slate-400 uppercase font-semibold">Method &amp; Segment</span>
                <span className="text-slate-300 uppercase">
                  {details.payment?.method} | {details.payment?.customer_segment}
                </span>
              </div>
            </div>

            {/* 1. FINANCIAL TRUTH */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-emerald-400 uppercase font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Financial Truth
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    details.financial_state === 'VERIFIED_LOST'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                      : details.financial_state === 'ALREADY_RECOVERED'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : details.financial_state === 'UNCERTAIN'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                  }`}
                >
                  {details.financial_state}
                </span>
              </div>
              <div className="text-[11px] text-slate-300 space-y-0.5">
                <div>
                  <span className="text-slate-500">Source: </span>
                  <span className="text-white font-semibold">Financial State Engine</span>
                </div>
                <div>
                  <span className="text-slate-500">Rule: </span>
                  <span className="text-cyan-300 font-semibold">{details.financial_rule_id || 'STATE-RULE-005'}</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-400 font-sans">{details.financial_state_reason}</p>
            </div>

            {/* 2. RECOVERY INTELLIGENCE */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] text-indigo-400 uppercase font-bold flex items-center gap-1.5">
                  <DollarSign className="w-3.5 h-3.5" />
                  Recovery Intelligence
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    details.recovery_decision === 'RECOVERY_WORTHWHILE'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {details.recovery_decision}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                <div>
                  <span className="text-slate-500">Probability: </span>
                  <span className="text-slate-200 font-bold">
                    {details.recovery_probability !== null && details.recovery_probability !== undefined
                      ? `${(details.recovery_probability * 100).toFixed(1)}%`
                      : 'N/A (Bypassed)'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">Expected Net Value: </span>
                  <span
                    className={`font-bold ${
                      (details.expected_net_value || 0) > 0 ? 'text-emerald-300' : 'text-slate-400'
                    }`}
                  >
                    {details.expected_net_value !== null && details.expected_net_value !== undefined
                      ? `₹${details.expected_net_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                      : 'N/A (Bypassed)'}
                  </span>
                </div>
              </div>
            </div>

            {/* 3. AGENT PLAN & 4. FIREWALL */}
            {trace && (
              <div className="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-3">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-amber-400 uppercase font-bold flex items-center gap-1.5">
                      <Brain className="w-3.5 h-3.5" />
                      Agent Plan (Advisory)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-bold">
                      {trace.plan.agent_action}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-300 font-sans italic">&ldquo;{trace.plan.agent_reason}&rdquo;</p>
                </div>

                <div className="pt-2 border-t border-white/5">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-rose-400 uppercase font-bold flex items-center gap-1.5">
                      <Lock className="w-3.5 h-3.5" />
                      Recovery Firewall
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      trace.guard.firewall_decision === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : 'bg-rose-500/20 text-rose-300'
                    }`}>
                      {trace.guard.firewall_decision}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 font-sans">{trace.guard.firewall_reason}</p>
                </div>
              </div>
            )}

            {/* 5. EXECUTION & 6. VERIFICATION */}
            {trace && (
              <div className="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-cyan-400 uppercase font-bold flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5" />
                    Verification &amp; Final Outcome
                  </span>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-extrabold text-[10px]">
                    {trace.verify.final_result}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div>
                    <span className="text-slate-500">Execution: </span>
                    <span className="text-slate-300">{trace.act.execution_status}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Verified State: </span>
                    <span className="text-slate-200 font-bold">{trace.verify.verification_state}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Event Stream History */}
            <div className="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-2">
              <span className="text-[10px] text-slate-400 uppercase font-bold flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                Raw Event Stream ({details.events?.length || 0} events)
              </span>
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {details.events?.map((ev: any, idx: number) => (
                  <div key={idx} className="p-2 rounded bg-slate-950/60 border border-white/5 flex items-center justify-between text-[10px]">
                    <span className="text-slate-200 font-bold">{ev.event}</span>
                    <span className="text-slate-500">{ev.ts}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-20 text-center text-slate-400 font-sans">No details available.</div>
        )}
      </div>

      {/* Action Footer */}
      {details && details.payment && (
        <div className="pt-4 border-t border-white/10 mt-4">
          <button
            onClick={() => onRunRecovery(details.payment.payment_id)}
            disabled={isRunning}
            className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs uppercase tracking-wider font-mono shadow-lg shadow-emerald-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-slate-950" />
            <span>{isRunning ? 'Processing Pipeline...' : 'Run Closed-Loop Recovery'}</span>
          </button>
        </div>
      )}
    </div>
  );
};
