import React, { useState } from 'react';
import { X, Database, Search, ShieldCheck, CheckCircle2, XCircle, ShieldAlert, ArrowDown } from 'lucide-react';
import { AuditEntry } from '../types';

interface AuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
  entries: AuditEntry[];
}

export const AuditTrailModal: React.FC<AuditTrailModalProps> = ({ isOpen, onClose, entries }) => {
  const [filterQuery, setFilterQuery] = useState('');

  if (!isOpen) return null;

  const filtered = entries.filter(
    (e) =>
      e.payment_id.toLowerCase().includes(filterQuery.toLowerCase()) ||
      e.final_result.toLowerCase().includes(filterQuery.toLowerCase()) ||
      (e.firewall_rule && e.firewall_rule.toLowerCase().includes(filterQuery.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="glass-card rounded-2xl w-full max-w-5xl max-h-[85vh] flex flex-col border border-white/20 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white font-mono flex items-center gap-2">
                IMMUTABLE AUDIT TRAIL LOG
              </h2>
              <p className="text-xs text-slate-400">
                Append-only ledger of all closed-loop evaluations, firewall decisions, and verified recoveries
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="p-4 border-b border-white/5 bg-slate-950/40 flex items-center justify-between">
          <div className="relative w-72">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter by ID, rule, or result..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-500 w-full"
            />
          </div>
          <span className="text-xs font-mono text-slate-400">
            Total Log Records: <span className="text-white font-bold">{filtered.length}</span>
          </span>
        </div>

        {/* Audit List */}
        <div className="p-4 overflow-y-auto space-y-3 flex-1">
          {filtered.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs font-mono">
              No audit records matching query.
            </div>
          ) : (
            filtered.map((entry, idx) => {
              const isSuccess = entry.final_result === 'RECOVERY_SUCCESS';
              const isFailed = entry.final_result === 'RECOVERY_FAILED';
              const isWithheld = !isSuccess && !isFailed;

              return (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/60 border border-white/5 font-mono text-xs hover:border-white/15 transition-all"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/5 pb-2.5 mb-2.5">
                    <div className="flex items-center gap-3">
                      <span className="text-slate-400 text-[11px]">
                        {new Date(entry.timestamp).toLocaleTimeString()}
                      </span>
                      <span className="text-white font-bold text-sm">{entry.payment_id}</span>
                      <span className="text-slate-400 text-[11px]">
                        ₹{entry.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2.5 py-0.5 rounded text-[10px] font-bold ${
                          isSuccess
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : isFailed
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                        }`}
                      >
                        {entry.final_result}
                      </span>
                    </div>
                  </div>

                  {/* Flow Trace */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px]">
                    <div>
                      <span className="text-slate-500 block text-[10px]">Initial State</span>
                      <span className="text-slate-200 font-semibold">{entry.initial_financial_state}</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">ML Probability & ENV</span>
                      <span className="text-slate-200">
                        {entry.recovery_probability ? `${Math.round(entry.recovery_probability * 100)}%` : 'N/A'} |{' '}
                        {entry.expected_net_value !== undefined ? `₹${Math.round(entry.expected_net_value)}` : 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Agent & Firewall</span>
                      <span className="text-indigo-300 font-semibold">{entry.agent_action || 'STOP'}</span>{' '}
                      <span className="text-slate-400">({entry.firewall_decision})</span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[10px]">Verified State</span>
                      <span className="text-emerald-300 font-semibold">{entry.verification_state}</span>
                    </div>
                  </div>

                  {entry.agent_reason && (
                    <div className="mt-2.5 text-[11px] text-slate-400 font-sans italic bg-black/20 p-2 rounded">
                      &ldquo;{entry.agent_reason}&rdquo;
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
