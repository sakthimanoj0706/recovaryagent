import React, { useState } from 'react';
import { Radio, RefreshCw, Send, ShieldAlert, CheckCircle, ArrowRight, Zap } from 'lucide-react';
import { postPaymentWebhook } from '../api';

export interface TimelineEventItem {
  time: string;
  event: string;
  payment_id: string;
  order_id?: string;
  amount: number;
  source: string;
  state_before?: string;
  state_after?: string;
  state_changed?: boolean;
  action?: string;
  verification?: string;
  simulation?: boolean;
  is_duplicate?: boolean;
}

interface EventStreamPanelProps {
  events: TimelineEventItem[];
  onRefresh: () => void;
  isLoading: boolean;
}

export const EventStreamPanel: React.FC<EventStreamPanelProps> = ({ events, onRefresh, isLoading }) => {
  const [isInjecting, setIsInjecting] = useState(false);
  const [lastInjectResult, setLastInjectResult] = useState<string | null>(null);

  // Quick webhook simulator injection buttons
  const injectWebhook = async (eventType: 'payment.failed' | 'payment.captured' | 'payment.authorized' | 'duplicate') => {
    setIsInjecting(true);
    setLastInjectResult(null);
    try {
      const pid = 'pay_ui_live_' + Math.floor(1000 + Math.random() * 9000);
      let payload: any;

      if (eventType === 'duplicate' && events.length > 0) {
        // Re-inject the last event
        const last = events[0];
        payload = {
          provider: last.source || 'mock',
          event_id: 'evt_dup_' + last.payment_id,
          event: last.event,
          payment_id: last.payment_id,
          amount: last.amount,
          ts: new Date().toISOString(),
        };
      } else {
        payload = {
          provider: 'mock',
          event_id: `evt_ui_${Date.now()}`,
          event: eventType,
          payment_id: pid,
          order_id: `ord_${pid}`,
          amount: 15000,
          method: 'upi',
          error_code: eventType === 'payment.failed' ? 'INSUFFICIENT_FUNDS' : undefined,
          hardness: eventType === 'payment.failed' ? 'soft' : undefined,
          late_authorization: eventType === 'payment.authorized' ? true : undefined,
          ts: new Date().toISOString(),
          payload: { channel: 'webhook_simulator', source: 'command_center' },
        };
      }

      const res = await postPaymentWebhook(payload);
      setLastInjectResult(`${res.status}: ${res.message || 'Webhook delivered successfully'}`);
      onRefresh();
    } catch (err: any) {
      setLastInjectResult(`Error: ${err.message}`);
    } finally {
      setIsInjecting(false);
    }
  };

  const getEventBadgeColor = (event: string) => {
    switch (event) {
      case 'payment.captured':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40';
      case 'payment.authorized':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
      case 'payment.failed':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/40';
      case 'payment.pending':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-slate-700/50 text-slate-300 border-slate-600';
    }
  };

  const getStateBadgeColor = (state?: string) => {
    switch (state) {
      case 'ALREADY_RECOVERED':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
      case 'VERIFIED_LOST':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/30';
      case 'UNCERTAIN':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
      case 'EXCEPTION':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      default:
        return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  };

  return (
    <div className="bg-[#0e1424] border border-white/10 rounded-xl p-5 shadow-lg backdrop-blur-sm space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
            <Radio className="w-5 h-5 text-cyan-400 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold font-mono text-white tracking-wide">
                REAL-TIME EVENT STREAM & WEBHOOK INGESTION
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                LIVE STREAM
              </span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                SIMULATION MODE
              </span>
            </div>
            <p className="text-xs text-slate-400 font-sans mt-0.5">
              Provider-independent ingestion pipeline with automatic deduplication, UTC normalization, and instant financial state re-evaluation.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => injectWebhook('payment.failed')}
            disabled={isInjecting}
            className="flex items-center gap-1 text-xs font-mono px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition-all disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>+ Failed Webhook</span>
          </button>

          <button
            onClick={() => injectWebhook('payment.captured')}
            disabled={isInjecting}
            className="flex items-center gap-1 text-xs font-mono px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-all disabled:opacity-50"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>+ Captured Webhook</span>
          </button>

          <button
            onClick={() => injectWebhook('duplicate')}
            disabled={isInjecting || events.length === 0}
            className="flex items-center gap-1 text-xs font-mono px-3 py-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition-all disabled:opacity-50"
          >
            <span>Idempotency Test</span>
          </button>

          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-white/10 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {lastInjectResult && (
        <div className="p-2.5 rounded-lg bg-cyan-950/40 border border-cyan-500/30 text-xs font-mono text-cyan-300 flex items-center justify-between">
          <span>{lastInjectResult}</span>
          <button onClick={() => setLastInjectResult(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono border-collapse">
          <thead>
            <tr className="border-b border-white/10 text-slate-400 uppercase text-[11px] bg-slate-900/40">
              <th className="py-2.5 px-3">TIME (UTC)</th>
              <th className="py-2.5 px-3">EVENT</th>
              <th className="py-2.5 px-3">PAYMENT ID</th>
              <th className="py-2.5 px-3">AMOUNT</th>
              <th className="py-2.5 px-3">SOURCE</th>
              <th className="py-2.5 px-3">STATE TRANSITION</th>
              <th className="py-2.5 px-3">AGENT ACTION</th>
              <th className="py-2.5 px-3">VERIFICATION</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {events.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500 font-mono">
                  No event stream records available. Trigger a webhook or run a recovery scenario above.
                </td>
              </tr>
            ) : (
              events.slice(0, 20).map((evt, i) => (
                <tr key={i} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-2 px-3 text-slate-400 whitespace-nowrap">
                    {evt.time ? new Date(evt.time).toLocaleTimeString() : 'NOW'}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded border text-[11px] font-semibold ${getEventBadgeColor(evt.event)}`}>
                      {evt.event}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-200 font-semibold whitespace-nowrap">
                    {evt.payment_id}
                  </td>
                  <td className="py-2 px-3 text-slate-300 font-semibold whitespace-nowrap">
                    ₹{evt.amount ? evt.amount.toLocaleString('en-IN') : '0'}
                  </td>
                  <td className="py-2 px-3 text-slate-400 whitespace-nowrap">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 border border-slate-700">
                      {evt.source || 'mock'}
                    </span>
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <div className="flex items-center gap-1 text-[10px]">
                      <span className={`px-1.5 py-0.5 rounded border ${getStateBadgeColor(evt.state_before)}`}>
                        {evt.state_before || 'NONE'}
                      </span>
                      <ArrowRight className="w-3 h-3 text-slate-500" />
                      <span className={`px-1.5 py-0.5 rounded border font-semibold ${getStateBadgeColor(evt.state_after)}`}>
                        {evt.state_after || 'UNKNOWN'}
                      </span>
                      {evt.state_changed && (
                        <span className="px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 text-[9px] border border-amber-500/40">
                          STATE CHANGED
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 text-[10px]">
                      {evt.action || 'NONE'}
                    </span>
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className="text-[10px] font-semibold text-emerald-400 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3 text-emerald-400" />
                      {evt.verification || 'VERIFIED'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
