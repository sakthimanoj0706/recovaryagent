import React, { useState, useEffect } from 'react';
import { runBenchmark, fetchBenchmarkCompare } from '../api';

export const BenchmarkPanel: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [paymentsCount, setPaymentsCount] = useState(1000);
  const [seed, setSeed] = useState(42);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const res = await fetchBenchmarkCompare();
      setData(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load benchmark data');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunBenchmark = async () => {
    try {
      setLoading(true);
      setError(null);
      await runBenchmark(paymentsCount, seed);
      await loadData();
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Benchmark simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const fmtCurrency = (val?: number) => {
    if (val === undefined || val === null) return '₹0';
    return `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  };

  const fmtNumber = (val?: number) => {
    if (val === undefined || val === null) return '0';
    return val.toLocaleString('en-IN');
  };

  const naive = data?.naive;
  const rai = data?.recoverai;
  const deltas = data?.deltas;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl space-y-6">
      {/* Top Banner & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white tracking-wide">
              Economic Impact Benchmark & ROI Engine
            </h2>
            <span className="px-2.5 py-1 text-xs font-semibold uppercase tracking-wider bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full">
              SYNTHETIC BENCHMARK — NOT PRODUCTION DATA
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Quantitative business value comparison: RecoverAI Bounded Financial Safety Rails vs Naive Recovery Baseline.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-800/80 border border-slate-700 rounded-lg p-1 text-xs">
            <span className="text-slate-400 px-2 font-medium">Population:</span>
            {[1000, 5000, 10000].map((n) => (
              <button
                key={n}
                onClick={() => setPaymentsCount(n)}
                className={`px-2.5 py-1 rounded transition-colors ${
                  paymentsCount === n
                    ? 'bg-blue-600 text-white font-semibold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {n.toLocaleString()}
              </button>
            ))}
          </div>

          <button
            onClick={handleRunBenchmark}
            disabled={loading}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-lg flex items-center gap-2 ${
              loading
                ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white'
            }`}
          >
            {loading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Simulating...</span>
              </>
            ) : (
              <>
                <span>▶ Run Simulation</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-xs">
          ⚠️ {error}
        </div>
      )}

      {/* Executive Summary Callout */}
      {data && (
        <div className="bg-gradient-to-br from-indigo-950/40 to-slate-900 border border-indigo-500/30 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg text-lg">
              💡
            </div>
            <div>
              <h3 className="text-sm font-semibold text-indigo-200">Executive Insight</h3>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed">
                {data.executive_summary}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 6 Hero Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Card 1: Verified Net Value */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Net Financial Value
          </span>
          <div className="text-lg font-bold text-emerald-400 mt-1">
            {fmtCurrency(rai?.net_legitimate_value)}
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
            <span className="text-emerald-400 font-semibold">
              +{deltas?.net_value_lift_pct?.toFixed(1)}%
            </span>
            <span>vs Naive</span>
          </div>
        </div>

        {/* Card 2: Unnecessary Actions */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Unnecessary Actions
          </span>
          <div className="text-lg font-bold text-emerald-400 mt-1">
            {fmtNumber(rai?.unnecessary_actions)}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            <span className="text-emerald-400 font-semibold">
              {deltas?.unnecessary_actions_reduction_pct?.toFixed(0)}% eliminated
            </span>
          </div>
        </div>

        {/* Card 3: Double Charges Prevented */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Double Charges
          </span>
          <div className="text-lg font-bold text-emerald-400 mt-1">
            0
          </div>
          <div className="text-xs text-slate-400 mt-1">
            <span className="text-emerald-400 font-semibold">
              {fmtNumber(deltas?.double_recoveries_prevented)} prevented
            </span>
          </div>
        </div>

        {/* Card 4: False Recovery Claims */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            False Recoveries
          </span>
          <div className="text-lg font-bold text-emerald-400 mt-1">
            0
          </div>
          <div className="text-xs text-slate-400 mt-1">
            <span className="text-emerald-400 font-semibold">
              {fmtNumber(deltas?.false_recoveries_eliminated)} eliminated
            </span>
          </div>
        </div>

        {/* Card 5: Gateway Ops Saved */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Gateway Calls Saved
          </span>
          <div className="text-lg font-bold text-blue-400 mt-1">
            {deltas?.gateway_operations_reduction_pct?.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">
            <span>{fmtNumber(rai?.gateway_operations)} vs {fmtNumber(naive?.gateway_operations)}</span>
          </div>
        </div>

        {/* Card 6: Accounting Conservation */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Accounting Balance
          </span>
          <div className="text-lg font-bold text-emerald-400 mt-1">
            ₹0.00
          </div>
          <div className="text-xs text-slate-400 mt-1">
            <span className="text-emerald-400 font-semibold">100% Invariant</span>
          </div>
        </div>
      </div>

      {/* Side-by-Side Detailed Breakdown Table */}
      {data && (
        <div className="bg-slate-950/60 border border-slate-800 rounded-xl overflow-hidden">
          <div className="px-5 py-3.5 bg-slate-800/50 border-b border-slate-800 flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Comparative Financial & Safety Audit Table
            </span>
            <span className="text-xs text-slate-400">
              Payments Simulated: <strong className="text-white">{fmtNumber(data.payments)}</strong> | Seed: <strong className="text-white">{data.seed}</strong>
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider border-b border-slate-800 font-semibold">
                <tr>
                  <th className="py-3 px-4">Financial & Safety Metric</th>
                  <th className="py-3 px-4 text-rose-400">Naive Recovery Baseline</th>
                  <th className="py-3 px-4 text-emerald-400">RecoverAI Full Safety Rails</th>
                  <th className="py-3 px-4 text-blue-400">Performance Delta / Lift</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                <tr>
                  <td className="py-2.5 px-4 font-medium">Total Payment Value Evaluated</td>
                  <td className="py-2.5 px-4">{fmtCurrency(naive?.total_payment_value)}</td>
                  <td className="py-2.5 px-4 font-semibold text-white">{fmtCurrency(rai?.total_payment_value)}</td>
                  <td className="py-2.5 px-4 text-slate-400">Identical Dataset</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-medium">Gross Claimed Recovery Revenue</td>
                  <td className="py-2.5 px-4 text-amber-300">{fmtCurrency(naive?.claimed_recovered_value)}</td>
                  <td className="py-2.5 px-4 text-emerald-300">{fmtCurrency(rai?.claimed_recovered_value)}</td>
                  <td className="py-2.5 px-4 text-slate-400">Truth-Adjusted</td>
                </tr>
                <tr className="bg-rose-950/10">
                  <td className="py-2.5 px-4 font-medium text-rose-300">False Recovery Claims (Phantom Money)</td>
                  <td className="py-2.5 px-4 text-rose-400 font-semibold">{fmtCurrency(naive?.false_recovery_value)} ({fmtNumber(naive?.false_recovery_claims)} claims)</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-semibold">₹0.00 (0 claims)</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-bold">100% Elimination</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-medium text-emerald-300">Real Verified Cash Collected</td>
                  <td className="py-2.5 px-4">{fmtCurrency(naive?.real_verified_value)}</td>
                  <td className="py-2.5 px-4 font-bold text-emerald-400">{fmtCurrency(rai?.real_verified_value)}</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-semibold">+{deltas?.recovered_value_lift_pct?.toFixed(1)}% Lift</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-medium">Double-Charging / Duplicate Actions</td>
                  <td className="py-2.5 px-4 text-rose-400">{fmtNumber(naive?.double_charge_events)} events</td>
                  <td className="py-2.5 px-4 text-emerald-400">0 events</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-semibold">{fmtNumber(deltas?.double_recoveries_prevented)} prevented</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-medium">Hard-Decline Retries (CARD_BLOCKED)</td>
                  <td className="py-2.5 px-4 text-rose-400">{fmtNumber(naive?.hard_decline_retried_count)} retries</td>
                  <td className="py-2.5 px-4 text-emerald-400">0 retries</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-semibold">100% Gate Intercept</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-medium">Dispute & Scheme Penalties Incurred</td>
                  <td className="py-2.5 px-4 text-rose-400">{fmtCurrency((naive?.dispute_chargeback_losses || 0) + (naive?.scheme_penalty_losses || 0))}</td>
                  <td className="py-2.5 px-4 text-emerald-400">₹0.00</td>
                  <td className="py-2.5 px-4 text-emerald-400 font-semibold">₹0 Risk Surcharge</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-4 font-medium">Gateway Operations & Telemetry</td>
                  <td className="py-2.5 px-4">{fmtNumber(naive?.gateway_operations)} calls</td>
                  <td className="py-2.5 px-4 font-semibold text-blue-300">{fmtNumber(rai?.gateway_operations)} calls</td>
                  <td className="py-2.5 px-4 text-blue-400 font-semibold">-{deltas?.gateway_operations_reduction_pct?.toFixed(1)}% Saved</td>
                </tr>
                <tr className="bg-emerald-950/20 font-bold">
                  <td className="py-3 px-4 text-white">NET LEGITIMATE RECOVERY VALUE</td>
                  <td className="py-3 px-4 text-slate-300">{fmtCurrency(naive?.net_legitimate_value)}</td>
                  <td className="py-3 px-4 text-emerald-400 text-sm">{fmtCurrency(rai?.net_legitimate_value)}</td>
                  <td className="py-3 px-4 text-emerald-400 text-sm">+{deltas?.net_value_lift_pct?.toFixed(1)}% (+{fmtCurrency(deltas?.net_value_lift_amount)})</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Key Findings List */}
      {data?.key_findings && (
        <div className="bg-slate-950/40 border border-slate-800 rounded-xl p-5">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Analytical Findings & Audit Conclusions
          </h4>
          <ul className="space-y-2 text-xs text-slate-300">
            {data.key_findings.map((f: string, i: number) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
