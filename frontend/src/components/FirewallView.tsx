import React from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

export const FirewallView: React.FC = () => {
  const rules = [
    {
      payment_id: 'pay_demo_001',
      action: 'PAYMENT_LINK',
      decision: 'APPROVED',
      rule: 'FIREWALL-001',
      reason: 'State confirmed VERIFIED_LOST + positive ENV (₹9,598). Action permitted.',
      amount: '₹10,000.00',
    },
    {
      payment_id: 'pay_demo_003',
      action: 'RETRY',
      decision: 'STOP',
      rule: 'FIREWALL-006',
      reason: 'Payment already recovered via late auth. Halting unnecessary actions.',
      amount: '₹7,499.00',
    },
    {
      payment_id: 'pay_demo_004',
      action: 'STOP',
      decision: 'STOP',
      rule: 'FIREWALL-002',
      reason: 'Negative expected net value (-₹75.17). Pursuit economically irrational.',
      amount: '₹50.00',
    },
    {
      payment_id: 'pay_demo_005',
      action: 'RETRY',
      decision: 'STOP',
      rule: 'FIREWALL-004',
      reason: 'Hard decline confirmed (CARD_BLOCKED). Automated RETRY prohibited.',
      amount: '₹12,000.00',
    },
    {
      payment_id: 'pay_demo_006',
      action: 'RETRY',
      decision: 'STOP',
      rule: 'FIREWALL-005',
      reason: 'Maximum retry limit reached (3 >= 3). Halting gateway spam.',
      amount: '₹5,000.00',
    },
    {
      payment_id: 'pay_demo_dup',
      action: 'PAYMENT_LINK',
      decision: 'STOP',
      rule: 'FIREWALL-009',
      reason: 'Duplicate action already pending. Preventing customer notification spam.',
      amount: '₹8,000.00',
    },
  ];

  return (
    <div className="glass-card rounded-2xl p-6 border border-white/10 relative overflow-hidden">
      <div className="flex items-center justify-between mb-5 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-base font-semibold text-white flex items-center gap-2 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            RECOVERY FIREWALL POLICIES
          </h2>
          <p className="text-xs text-slate-400 mt-0.5 font-sans">
            Deterministic rule enforcement preventing invalid interventions and protecting customer trust
          </p>
        </div>
        <span className="text-[10px] font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-white/10">
          RULES 001 - 010 ACTIVE
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-white/10 text-slate-400">
              <th className="pb-3 font-semibold">Payment</th>
              <th className="pb-3 font-semibold">Proposed Action</th>
              <th className="pb-3 font-semibold">Decision</th>
              <th className="pb-3 font-semibold">Rule ID</th>
              <th className="pb-3 font-semibold">Reason</th>
              <th className="pb-3 font-semibold text-right">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rules.map((r, i) => (
              <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                <td className="py-3 text-slate-200 font-bold">{r.payment_id}</td>
                <td className="py-3 text-indigo-300 font-semibold">{r.action}</td>
                <td className="py-3">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    r.decision === 'APPROVED'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  }`}>
                    {r.decision}
                  </span>
                </td>
                <td className="py-3 text-slate-400">{r.rule}</td>
                <td className="py-3 text-slate-300 max-w-md font-sans text-[11px] truncate">
                  {r.reason}
                </td>
                <td className="py-3 text-right text-slate-100 font-bold">{r.amount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
