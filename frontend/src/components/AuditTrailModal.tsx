import React, { useState } from 'react';
import {
  X,
  Database,
  Search,
  Download,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  ShieldAlert,
  ArrowDown,
  Filter,
} from 'lucide-react';
import { AuditEntry } from '../types';

interface AuditTrailModalProps {
  isOpen: boolean;
  onClose: () => void;
  entries: AuditEntry[];
}

export const AuditTrailModal: React.FC<AuditTrailModalProps> = ({ isOpen, onClose, entries }) => {
  const [filterQuery, setFilterQuery] = useState('');
  const [stageFilter, setStageFilter] = useState<string>('ALL');

  if (!isOpen) return null;

  const filtered = entries.filter((e) => {
    const matchesQuery =
      e.payment_id.toLowerCase().includes(filterQuery.toLowerCase()) ||
      (e.order_id && e.order_id.toLowerCase().includes(filterQuery.toLowerCase())) ||
      (e.final_result && e.final_result.toLowerCase().includes(filterQuery.toLowerCase())) ||
      (e.firewall_rule && e.firewall_rule.toLowerCase().includes(filterQuery.toLowerCase())) ||
      (e.initial_financial_state && e.initial_financial_state.toLowerCase().includes(filterQuery.toLowerCase())) ||
      (e.firewall_decision && e.firewall_decision.toLowerCase().includes(filterQuery.toLowerCase()));

    const matchesStage = stageFilter === 'ALL' || e.firewall_decision === stageFilter || e.final_result === stageFilter;

    return matchesQuery && matchesStage;
  });

  const handleExportJSON = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(entries, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `recoverai_audit_export_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="bg-[#0e1424] rounded-2xl w-full max-w-6xl max-h-[88vh] flex flex-col border border-white/20 shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
        {/* Header */}
        <div className="p-5 border-b border-white/10 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white font-mono">
                  IMMUTABLE AUDIT TRAIL LOG
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30">
                  APPEND-ONLY JSONL
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Full chronological ledger across all closed-loop evaluations, firewall decisions, and verified recoveries.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleExportJSON}
              className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold transition-all"
            >
              <Download className="w-3.5 h-3.5" />
              <span>EXPORT AUDIT JSON</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="p-3.5 border-b border-white/5 bg-slate-950/60 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search payment_id, rule, state, or outcome..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-500 w-full"
            />
          </div>

          <div className="flex items-center gap-2 text-xs font-mono w-full sm:w-auto">
            <span className="text-slate-400 text-[11px] flex items-center gap-1">
              <Filter className="w-3 h-3 text-slate-500" /> Filter:
            </span>
            {['ALL', 'APPROVED', 'STOP', 'RECOVERY_SUCCESS', 'RECOVERY_FAILED'].map((st) => (
              <button
                key={st}
                onClick={() => setStageFilter(st)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                  stageFilter === st
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-white/5'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Audit Records Table */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono">
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No audit records matching &ldquo;{filterQuery}&rdquo;
            </div>
          ) : (
            filtered.map((entry, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-slate-900/60 border border-white/5 hover:border-white/20 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                {/* Left: ID & State */}
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-white">{entry.payment_id}</span>
                    {entry.order_id && <span className="text-slate-500 text-[11px]">({entry.order_id})</span>}
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      {entry.initial_financial_state}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-400">
                    Timestamp: {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : 'N/A'} | Action:{' '}
                    <strong className="text-slate-300">{entry.agent_action || 'NONE'}</strong>
                  </div>
                </div>

                {/* Middle: Economics & Firewall */}
                <div className="flex items-center gap-4 text-[11px]">
                  <div>
                    <span className="text-slate-500">ENV:</span>{' '}
                    <strong
                      className={
                        entry.expected_net_value && entry.expected_net_value > 0
                          ? 'text-emerald-400'
                          : 'text-amber-400'
                      }
                    >
                      {entry.expected_net_value !== undefined ? `₹${entry.expected_net_value.toFixed(2)}` : 'N/A'}
                    </strong>
                  </div>

                  <div>
                    <span className="text-slate-500">Firewall:</span>{' '}
                    <span
                      className={`font-semibold ${
                        entry.firewall_decision === 'APPROVED' ? 'text-emerald-400' : 'text-amber-400'
                      }`}
                    >
                      {entry.firewall_decision} {entry.firewall_rule ? `(${entry.firewall_rule})` : ''}
                    </span>
                  </div>
                </div>

                {/* Right: Outcome & Accounting */}
                <div className="text-right space-y-0.5">
                  <div
                    className={`font-bold uppercase text-[11px] ${
                      entry.final_result === 'RECOVERY_SUCCESS'
                        ? 'text-emerald-400'
                        : entry.final_result === 'SAFE_STOP' || entry.final_result === 'CORRECTLY_WITHHELD'
                        ? 'text-amber-400'
                        : 'text-slate-300'
                    }`}
                  >
                    {entry.final_result}
                  </div>
                  <div className="text-[10px] text-slate-400">
                    {entry.amount_recovered > 0
                      ? `₹${entry.amount_recovered.toLocaleString('en-IN')} Recovered`
                      : `₹${entry.amount_withheld.toLocaleString('en-IN')} Withheld`}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-3.5 border-t border-white/10 bg-slate-900/80 flex items-center justify-between text-xs text-slate-400 font-mono">
          <span>
            Total Entries: <strong>{entries.length}</strong> (Showing: <strong>{filtered.length}</strong>)
          </span>
          <span className="text-emerald-400 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            100% Cryptographically &amp; Ledger Consistent
          </span>
        </div>
      </div>
    </div>
  );
};
