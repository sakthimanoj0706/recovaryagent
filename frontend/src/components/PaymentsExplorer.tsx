import React, { useState } from 'react';
import { Search, Filter, Play, ExternalLink, CreditCard, ChevronRight } from 'lucide-react';
import { PaymentItem } from '../types';

interface PaymentsExplorerProps {
  payments: PaymentItem[];
  onSelectPayment: (paymentId: string) => void;
  onRunPayment: (paymentId: string) => void;
  selectedPaymentId?: string;
  isLoading: boolean;
}

export const PaymentsExplorer: React.FC<PaymentsExplorerProps> = ({
  payments,
  onSelectPayment,
  onRunPayment,
  selectedPaymentId,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterState, setFilterState] = useState('ALL');

  const filtered = payments.filter((p) => {
    const matchSearch =
      p.payment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.order_id && p.order_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      p.error_code.toLowerCase().includes(searchTerm.toLowerCase());

    const matchState = filterState === 'ALL' || p.financial_state === filterState;

    return matchSearch && matchState;
  });

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-5 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2 font-mono">
            <CreditCard className="w-4 h-4 text-cyan-400" />
            PAYMENT INVESTIGATION & DATASET EXPLORER
          </h2>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Real production-like dataset records with evaluated financial states and lifecycle events
          </p>
        </div>

        {/* Search & State Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search ID or error code..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-900 border border-white/10 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-500 w-52"
            />
          </div>

          <select
            value={filterState}
            onChange={(e) => setFilterState(e.target.value)}
            className="bg-slate-900 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-500 cursor-pointer"
          >
            <option value="ALL">All States</option>
            <option value="VERIFIED_LOST">VERIFIED_LOST</option>
            <option value="ALREADY_RECOVERED">ALREADY_RECOVERED</option>
            <option value="UNCERTAIN">UNCERTAIN</option>
            <option value="EXCEPTION">EXCEPTION</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="sticky top-0 bg-slate-900/90 backdrop-blur z-10 border-b border-white/10 text-slate-400">
            <tr>
              <th className="py-2.5 px-3 font-semibold">Payment ID</th>
              <th className="py-2.5 px-3 font-semibold">Order ID</th>
              <th className="py-2.5 px-3 font-semibold">Amount</th>
              <th className="py-2.5 px-3 font-semibold">Method</th>
              <th className="py-2.5 px-3 font-semibold">Failure Reason</th>
              <th className="py-2.5 px-3 font-semibold">Financial State</th>
              <th className="py-2.5 px-3 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filtered.slice(0, 30).map((p) => {
              const isSelected = selectedPaymentId === p.payment_id;

              return (
                <tr
                  key={p.payment_id}
                  onClick={() => onSelectPayment(p.payment_id)}
                  className={`hover:bg-white/[0.04] cursor-pointer transition-colors ${
                    isSelected ? 'bg-cyan-950/40 border-l-2 border-cyan-400' : ''
                  }`}
                >
                  <td className="py-2.5 px-3 text-slate-200 font-bold">{p.payment_id}</td>
                  <td className="py-2.5 px-3 text-slate-400">{p.order_id || 'N/A'}</td>
                  <td className="py-2.5 px-3 text-white font-bold">
                    ₹{p.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="py-2.5 px-3 uppercase text-slate-300">{p.method}</td>
                  <td className="py-2.5 px-3">
                    <span className="text-slate-300">{p.error_code}</span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        p.financial_state === 'VERIFIED_LOST'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : p.financial_state === 'ALREADY_RECOVERED'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : p.financial_state === 'UNCERTAIN'
                          ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                      }`}
                    >
                      {p.financial_state}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRunPayment(p.payment_id);
                      }}
                      disabled={isLoading}
                      className="px-2.5 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-medium inline-flex items-center gap-1 transition-all disabled:opacity-50"
                    >
                      <Play className="w-3 h-3 fill-emerald-300" />
                      <span>Run</span>
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
