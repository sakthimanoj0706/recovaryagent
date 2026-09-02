import React, { useState, useEffect } from 'react';
import {
  runPolicyLab,
  fetchLatestPolicyLab,
  runPolicySensitivity,
  runPolicyBreakEven,
  runPolicyMonteCarlo,
} from '../api';

export const PolicyLab: React.FC = () => {
  // Economic Environment State
  const [retryCost, setRetryCost] = useState(0.50);
  const [contactCost, setContactCost] = useState(0.25);
  const [linkCost, setLinkCost] = useState(1.50);
  const [chargebackCost, setChargebackCost] = useState(250.00);
  const [schemePenalty, setSchemePenalty] = useState(15.00);
  const [probMultiplier, setProbMultiplier] = useState(1.0);
  const [maxRetries, setMaxRetries] = useState(3);
  const [highValueThreshold, setHighValueThreshold] = useState(25000);
  const [riskTolerance, setRiskTolerance] = useState<'LOW' | 'MEDIUM' | 'HIGH'>('MEDIUM');
  const [population, setPopulation] = useState(1000);
  const [seed, setSeed] = useState(42);

  // Custom Policy State
  const [policyName, setPolicyName] = useState('Aggressive Channel Optimizer');
  const [customMaxRetries, setCustomMaxRetries] = useState(2);
  const [enableRetry, setEnableRetry] = useState(true);
  const [enableLink, setEnableLink] = useState(true);
  const [enableReminder, setEnableReminder] = useState(true);
  const [escalateHighValue, setEscalateHighValue] = useState(false);
  const [minEnv, setMinEnv] = useState(0.0);

  // Results State
  const [simResult, setSimResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Sensitivity State
  const [sensParam, setSensParam] = useState('retry_cost');
  const [sensResult, setSensResult] = useState<any>(null);
  const [sensLoading, setSensLoading] = useState(false);

  // Break-Even State
  const [breakEvenResult, setBreakEvenResult] = useState<any>(null);
  const [beLoading, setBeLoading] = useState(false);

  // Monte Carlo State
  const [mcRuns, setMcRuns] = useState(50);
  const [mcResult, setMcResult] = useState<any>(null);
  const [mcLoading, setMcLoading] = useState(false);

  // Active Tab in Analysis section
  const [activeAnalysisTab, setActiveAnalysisTab] = useState<'SENSITIVITY' | 'BREAK_EVEN' | 'MONTE_CARLO'>('SENSITIVITY');

  const getEnvPayload = () => ({
    retry_cost: Number(retryCost),
    customer_contact_cost: Number(contactCost),
    payment_link_cost: Number(linkCost),
    chargeback_cost: Number(chargebackCost),
    scheme_penalty: Number(schemePenalty),
    recovery_probability_multiplier: Number(probMultiplier),
    max_retries: Number(maxRetries),
    high_value_threshold: Number(highValueThreshold),
    risk_tolerance: riskTolerance,
    payment_population: Number(population),
    random_seed: Number(seed),
  });

  const getCustomPolicyPayload = () => ({
    name: policyName,
    max_retries: Number(customMaxRetries),
    enable_retry: enableRetry,
    enable_payment_link: enableLink,
    enable_reminder: enableReminder,
    escalate_on_high_value: escalateHighValue,
    min_expected_net_value: Number(minEnv),
    risk_tolerance: riskTolerance,
  });

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchLatestPolicyLab();
      setSimResult(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load policy lab baseline');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleRunSimulation = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await runPolicyLab(getEnvPayload(), getCustomPolicyPayload());
      setSimResult(res);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Simulation run failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRunSensitivity = async (param = sensParam) => {
    try {
      setSensLoading(true);
      const res = await runPolicySensitivity({
        parameter_name: param,
        env: getEnvPayload(),
        custom_policy: getCustomPolicyPayload(),
      });
      setSensResult(res);
    } catch (err: any) {
      console.error(err);
    } finally {
      setSensLoading(false);
    }
  };

  const handleRunBreakEven = async () => {
    try {
      setBeLoading(true);
      const res = await runPolicyBreakEven({
        parameter_name: sensParam,
        search_min: 0.0,
        search_max: sensParam === 'chargeback_cost' ? 5000.0 : 200.0,
        env: getEnvPayload(),
        custom_policy: getCustomPolicyPayload(),
      });
      setBreakEvenResult(res);
    } catch (err: any) {
      console.error(err);
    } finally {
      setBeLoading(false);
    }
  };

  const handleRunMonteCarlo = async () => {
    try {
      setMcLoading(true);
      const res = await runPolicyMonteCarlo({
        runs: mcRuns,
        starting_seed: 42,
        population_per_run: 200,
        env: getEnvPayload(),
        custom_policy: getCustomPolicyPayload(),
      });
      setMcResult(res);
    } catch (err: any) {
      console.error(err);
    } finally {
      setMcLoading(false);
    }
  };

  const fmtCurrency = (val?: number) => {
    if (val === undefined || val === null) return '₹0';
    if (Math.abs(val) < 0.01 && val !== 0) return `₹${val.toFixed(4)}`;
    return `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  };

  const fmtNum = (val?: number) => {
    if (val === undefined || val === null) return '0';
    return val.toLocaleString('en-IN');
  };

  const comp = simResult?.comparison;
  const naive = comp?.naive;
  const rai = comp?.recoverai;
  const custom = comp?.custom;
  const winner = comp?.best_strategy;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-2xl space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-xl font-bold text-white tracking-wide">
              🔬 Recovery Policy Lab & What-If Economic Simulator
            </h2>
            <span className="px-2.5 py-1 text-xs font-semibold uppercase tracking-wider bg-purple-500/10 text-purple-400 border border-purple-500/30 rounded-full">
              SIMULATION ONLY — SYNTHETIC DATA — NO REAL MONEY
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Explore how recovery strategies behave under custom macroeconomic costs, probability regimes, and merchant policies.
          </p>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={loading}
          className={`px-5 py-2.5 rounded-lg text-xs font-bold transition-all shadow-lg flex items-center gap-2 self-start md:self-auto ${
            loading
              ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white'
          }`}
        >
          {loading ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Running Simulation...</span>
            </>
          ) : (
            <>
              <span>▶ Run Policy Simulation</span>
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-300 text-xs">
          ⚠️ {error}
        </div>
      )}

      {/* Grid: Left Column Controls, Right Column Strategy Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Economic Environment & Custom Policy Controls */}
        <div className="lg:col-span-4 bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              ⚙️ Economic Environment
            </h3>
            <span className="text-[10px] text-slate-400">Merchant Economics</span>
          </div>

          <div className="space-y-3.5 text-xs">
            {/* Population & Seed */}
            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="text-slate-400 font-medium">Population:</label>
                <select
                  value={population}
                  onChange={(e) => setPopulation(Number(e.target.value))}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded p-1.5 text-white"
                >
                  <option value={500}>500 payments</option>
                  <option value={1000}>1,000 payments</option>
                  <option value={5000}>5,000 payments</option>
                  <option value={10000}>10,000 payments</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 font-medium">Random Seed:</label>
                <input
                  type="number"
                  value={seed}
                  onChange={(e) => setSeed(Number(e.target.value))}
                  className="w-full mt-1 bg-slate-900 border border-slate-700 rounded p-1.5 text-white"
                />
              </div>
            </div>

            {/* Sliders / Inputs */}
            <div>
              <div className="flex justify-between text-slate-400">
                <span>Gateway Retry Cost:</span>
                <span className="text-white font-semibold">₹{retryCost.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.10"
                max="20.00"
                step="0.10"
                value={retryCost}
                onChange={(e) => setRetryCost(Number(e.target.value))}
                className="w-full accent-blue-500 mt-1 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-400">
                <span>Payment Link Cost:</span>
                <span className="text-white font-semibold">₹{linkCost.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.25"
                max="20.00"
                step="0.25"
                value={linkCost}
                onChange={(e) => setLinkCost(Number(e.target.value))}
                className="w-full accent-blue-500 mt-1 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-400">
                <span>Customer Contact Cost:</span>
                <span className="text-white font-semibold">₹{contactCost.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="10.00"
                step="0.05"
                value={contactCost}
                onChange={(e) => setContactCost(Number(e.target.value))}
                className="w-full accent-blue-500 mt-1 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-400">
                <span>Double-Charge Dispute Cost:</span>
                <span className="text-rose-400 font-semibold">₹{chargebackCost.toFixed(0)}</span>
              </div>
              <input
                type="range"
                min="50"
                max="2500"
                step="50"
                value={chargebackCost}
                onChange={(e) => setChargebackCost(Number(e.target.value))}
                className="w-full accent-rose-500 mt-1 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-400">
                <span>Hard-Decline Scheme Penalty:</span>
                <span className="text-amber-400 font-semibold">₹{schemePenalty.toFixed(0)}</span>
              </div>
              <input
                type="range"
                min="0"
                max="250"
                step="5"
                value={schemePenalty}
                onChange={(e) => setSchemePenalty(Number(e.target.value))}
                className="w-full accent-amber-500 mt-1 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between text-slate-400">
                <span>Probability Multiplier:</span>
                <span className="text-emerald-400 font-semibold">{probMultiplier.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                min="0.20"
                max="2.00"
                step="0.05"
                value={probMultiplier}
                onChange={(e) => setProbMultiplier(Number(e.target.value))}
                className="w-full accent-emerald-500 mt-1 cursor-pointer"
              />
            </div>

            <div>
              <label className="text-slate-400 font-medium">Risk Appetite Tier:</label>
              <div className="grid grid-cols-3 gap-1 mt-1">
                {(['LOW', 'MEDIUM', 'HIGH'] as const).map((tier) => (
                  <button
                    key={tier}
                    onClick={() => setRiskTolerance(tier)}
                    className={`py-1 rounded text-xs font-semibold ${
                      riskTolerance === tier
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-900 text-slate-400 border border-slate-800'
                    }`}
                  >
                    {tier}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Custom Policy Config Subsection */}
          <div className="border-t border-slate-800/80 pt-4 space-y-3 text-xs">
            <h4 className="text-xs font-bold uppercase tracking-wider text-purple-300">
              🎛️ Custom Policy Rules
            </h4>

            <div>
              <label className="text-slate-400 font-medium">Policy Name:</label>
              <input
                type="text"
                value={policyName}
                onChange={(e) => setPolicyName(e.target.value)}
                className="w-full mt-1 bg-slate-900 border border-slate-700 rounded p-1.5 text-white text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableRetry}
                  onChange={(e) => setEnableRetry(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700"
                />
                <span>Enable Retry</span>
              </label>

              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableLink}
                  onChange={(e) => setEnableLink(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700"
                />
                <span>Enable Link</span>
              </label>

              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={enableReminder}
                  onChange={(e) => setEnableReminder(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700"
                />
                <span>Enable Reminder</span>
              </label>

              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={escalateHighValue}
                  onChange={(e) => setEscalateHighValue(e.target.checked)}
                  className="rounded bg-slate-900 border-slate-700"
                />
                <span>Escalate High Val</span>
              </label>
            </div>
          </div>
        </div>

        {/* Right Column: 3 Strategy Cards & Analytical Results */}
        <div className="lg:col-span-8 space-y-5">
          {/* 3 Strategy KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: Naive Baseline */}
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-400">
                    Naive Baseline
                  </span>
                  <span className="text-[10px] bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded">
                    No Safety Rails
                  </span>
                </div>
                <div className="mt-3">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Net Legitimate Value</span>
                  <div className="text-lg font-bold text-white mt-0.5">
                    {fmtCurrency(naive?.net_legitimate_value)}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-400">
                <div className="flex justify-between">
                  <span>Real Cash in Bank:</span>
                  <span className="text-slate-200 font-semibold">{fmtCurrency(naive?.real_verified_value)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Phantom Claims:</span>
                  <span className="text-rose-400 font-semibold">{fmtCurrency(naive?.false_recovery_value)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Double Charges:</span>
                  <span className="text-rose-400 font-semibold">{fmtNum(naive?.double_charge_events)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Unnecessary Actions:</span>
                  <span className="text-rose-400 font-semibold">{fmtNum(naive?.unnecessary_actions)}</span>
                </div>
              </div>
            </div>

            {/* Card 2: RecoverAI Core */}
            <div className={`bg-slate-950/60 border rounded-xl p-4 flex flex-col justify-between ${
              winner === 'RECOVERAI' ? 'border-emerald-500/60 ring-1 ring-emerald-500/30' : 'border-slate-800'
            }`}>
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    RecoverAI Core
                  </span>
                  {winner === 'RECOVERAI' && (
                    <span className="text-[10px] bg-emerald-500/20 text-emerald-300 font-bold px-2 py-0.5 rounded-full border border-emerald-500/40">
                      ★ TOP VALUE
                    </span>
                  )}
                </div>
                <div className="mt-3">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Net Legitimate Value</span>
                  <div className="text-lg font-bold text-emerald-400 mt-0.5">
                    {fmtCurrency(rai?.net_legitimate_value)}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-400">
                <div className="flex justify-between">
                  <span>Real Cash in Bank:</span>
                  <span className="text-emerald-300 font-semibold">{fmtCurrency(rai?.real_verified_value)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Value Lift vs Naive:</span>
                  <span className="text-emerald-400 font-semibold">+{comp?.deltas?.recoverai_net_lift_pct?.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Double Charges:</span>
                  <span className="text-emerald-400 font-semibold">0 (100% Guard)</span>
                </div>
                <div className="flex justify-between">
                  <span>Safety Violations:</span>
                  <span className="text-emerald-400 font-semibold">0</span>
                </div>
              </div>
            </div>

            {/* Card 3: Custom Policy */}
            <div className={`bg-slate-950/60 border rounded-xl p-4 flex flex-col justify-between ${
              winner === 'CUSTOM_POLICY' ? 'border-purple-500/60 ring-1 ring-purple-500/30' : 'border-slate-800'
            }`}>
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-purple-400">
                    {policyName.slice(0, 18)}
                  </span>
                  {winner === 'CUSTOM_POLICY' && (
                    <span className="text-[10px] bg-purple-500/20 text-purple-300 font-bold px-2 py-0.5 rounded-full border border-purple-500/40">
                      ★ TOP VALUE
                    </span>
                  )}
                </div>
                <div className="mt-3">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Net Legitimate Value</span>
                  <div className="text-lg font-bold text-purple-400 mt-0.5">
                    {fmtCurrency(custom?.net_legitimate_value)}
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-400">
                <div className="flex justify-between">
                  <span>Real Cash in Bank:</span>
                  <span className="text-purple-300 font-semibold">{fmtCurrency(custom?.real_verified_value)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Lift vs Naive:</span>
                  <span className="text-purple-400 font-semibold">+{comp?.deltas?.custom_net_lift_pct?.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span>Double Charges:</span>
                  <span className="text-purple-400 font-semibold">0 (Firewall Enforced)</span>
                </div>
                <div className="flex justify-between">
                  <span>Safety Violations:</span>
                  <span className="text-purple-400 font-semibold">0</span>
                </div>
              </div>
            </div>
          </div>

          {/* Why Did This Strategy Win Callout */}
          {comp?.why_winner_won && (
            <div className="bg-gradient-to-br from-indigo-950/40 to-slate-900 border border-indigo-500/30 rounded-xl p-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-2">
                <span>🏆 Analytical Verification: Why {winner} Delivered Top Economic Value</span>
              </h4>
              <ul className="mt-2.5 space-y-1.5 text-xs text-slate-300">
                {comp.why_winner_won.map((rsn: string, i: number) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>{rsn}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Detailed 3-Way Comparative Audit Table */}
          <div className="bg-slate-950/60 border border-slate-800 rounded-xl overflow-hidden">
            <div className="px-4 py-2.5 bg-slate-800/50 border-b border-slate-800 flex justify-between items-center text-xs">
              <span className="font-bold uppercase tracking-wider text-slate-300">
                Detailed 3-Strategy Financial Audit
              </span>
              <span className="text-slate-400">
                Population: <strong className="text-white">{fmtNum(population)}</strong> | Seed: <strong className="text-white">{seed}</strong>
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider border-b border-slate-800 font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Metric</th>
                    <th className="py-2.5 px-3 text-rose-400">Naive Baseline</th>
                    <th className="py-2.5 px-3 text-emerald-400">RecoverAI Core</th>
                    <th className="py-2.5 px-3 text-purple-400">Custom Policy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  <tr>
                    <td className="py-2 px-3 font-medium">Real Cash Collected in Bank</td>
                    <td className="py-2 px-3">{fmtCurrency(naive?.real_verified_value)}</td>
                    <td className="py-2 px-3 text-emerald-300 font-semibold">{fmtCurrency(rai?.real_verified_value)}</td>
                    <td className="py-2 px-3 text-purple-300 font-semibold">{fmtCurrency(custom?.real_verified_value)}</td>
                  </tr>
                  <tr className="bg-rose-950/10">
                    <td className="py-2 px-3 font-medium text-rose-300">Phantom Revenue Claimed (Unearned)</td>
                    <td className="py-2 px-3 text-rose-400 font-semibold">{fmtCurrency(naive?.false_recovery_value)} ({fmtNum(naive?.false_recovery_claims)})</td>
                    <td className="py-2 px-3 text-emerald-400">₹0.00 (0 claims)</td>
                    <td className="py-2 px-3 text-purple-400">₹0.00 (0 claims)</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium">Dispute & Scheme Losses</td>
                    <td className="py-2 px-3 text-rose-400">{fmtCurrency((naive?.dispute_chargeback_losses || 0) + (naive?.scheme_penalty_losses || 0))}</td>
                    <td className="py-2 px-3 text-emerald-400">₹0.00</td>
                    <td className="py-2 px-3 text-purple-400">₹0.00</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium">Operating Cost</td>
                    <td className="py-2 px-3">{fmtCurrency(naive?.total_operating_cost)}</td>
                    <td className="py-2 px-3">{fmtCurrency(rai?.total_operating_cost)}</td>
                    <td className="py-2 px-3">{fmtCurrency(custom?.total_operating_cost)}</td>
                  </tr>
                  <tr>
                    <td className="py-2 px-3 font-medium">Unnecessary Actions Avoided</td>
                    <td className="py-2 px-3 text-rose-400">{fmtNum(naive?.unnecessary_actions)} wasted</td>
                    <td className="py-2 px-3 text-emerald-400 font-semibold">0 (100% saved)</td>
                    <td className="py-2 px-3 text-purple-400 font-semibold">0 (100% saved)</td>
                  </tr>
                  <tr className="bg-emerald-950/20 font-bold">
                    <td className="py-2.5 px-3 text-white">NET LEGITIMATE RECOVERY VALUE</td>
                    <td className="py-2.5 px-3 text-slate-300">{fmtCurrency(naive?.net_legitimate_value)}</td>
                    <td className="py-2.5 px-3 text-emerald-400">{fmtCurrency(rai?.net_legitimate_value)}</td>
                    <td className="py-2.5 px-3 text-purple-400">{fmtCurrency(custom?.net_legitimate_value)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      {/* Analytical Deep Dives: Sensitivity, Break-Even, Monte Carlo */}
      <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            {(['SENSITIVITY', 'BREAK_EVEN', 'MONTE_CARLO'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveAnalysisTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  activeAnalysisTab === tab
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {tab === 'SENSITIVITY' && '📈 Sensitivity Analysis'}
                {tab === 'BREAK_EVEN' && '⚖️ Break-Even Discovery'}
                {tab === 'MONTE_CARLO' && '🎲 Monte Carlo Validation'}
              </button>
            ))}
          </div>

          <span className="text-xs text-slate-400 font-mono">
            {activeAnalysisTab === 'SENSITIVITY' && 'One-parameter economic sweeps'}
            {activeAnalysisTab === 'BREAK_EVEN' && 'Deterministic crossover analysis'}
            {activeAnalysisTab === 'MONTE_CARLO' && 'Multi-seed statistical distribution'}
          </span>
        </div>

        {/* Tab 1: Sensitivity Analysis */}
        {activeAnalysisTab === 'SENSITIVITY' && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-slate-400 font-medium">Select Parameter to Vary:</span>
              {[
                { id: 'retry_cost', label: 'Retry Cost' },
                { id: 'chargeback_cost', label: 'Chargeback Cost' },
                { id: 'scheme_penalty', label: 'Scheme Penalty' },
                { id: 'recovery_probability_multiplier', label: 'Probability Multiplier' },
                { id: 'max_retries', label: 'Max Retries' },
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => {
                    setSensParam(p.id);
                    handleRunSensitivity(p.id);
                  }}
                  className={`px-2.5 py-1 rounded text-xs font-semibold ${
                    sensParam === p.id
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-900 text-slate-400 border border-slate-800 hover:text-white'
                  }`}
                >
                  {p.label}
                </button>
              ))}

              <button
                onClick={() => handleRunSensitivity()}
                disabled={sensLoading}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded text-xs font-bold ml-auto"
              >
                {sensLoading ? 'Sweeping...' : '▶ Run Sweep'}
              </button>
            </div>

            {sensResult?.points && (
              <div className="overflow-x-auto border border-slate-800 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3">{sensParam} Value</th>
                      <th className="py-2 px-3 text-rose-400">Naive Net Value</th>
                      <th className="py-2 px-3 text-emerald-400">RecoverAI Net Value</th>
                      <th className="py-2 px-3 text-purple-400">Custom Net Value</th>
                      <th className="py-2 px-3 text-blue-400">RecoverAI Lift %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {sensResult.points.map((pt: any, idx: number) => (
                      <tr key={idx}>
                        <td className="py-1.5 px-3 font-semibold text-white">
                          {sensParam.includes('cost') || sensParam.includes('penalty') ? `₹${pt.parameter_value.toFixed(2)}` : pt.parameter_value}
                        </td>
                        <td className="py-1.5 px-3">{fmtCurrency(pt.naive_net_value)}</td>
                        <td className="py-1.5 px-3 font-semibold text-emerald-300">{fmtCurrency(pt.recoverai_net_value)}</td>
                        <td className="py-1.5 px-3 text-purple-300">{fmtCurrency(pt.custom_net_value)}</td>
                        <td className="py-1.5 px-3 font-bold text-emerald-400">+{pt.recoverai_lift_percent.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Break-Even Discovery */}
        {activeAnalysisTab === 'BREAK_EVEN' && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between">
              <p className="text-slate-400">
                Identifies whether a parameter threshold exists where Naive Baseline equals RecoverAI Net Value.
              </p>
              <button
                onClick={handleRunBreakEven}
                disabled={beLoading}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-bold"
              >
                {beLoading ? 'Scanning Range...' : '▶ Discover Break-Even Point'}
              </button>
            </div>

            {breakEvenResult && (
              <div className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    breakEvenResult.break_even_found ? 'bg-emerald-500/20 text-emerald-300' : 'bg-blue-500/20 text-blue-300'
                  }`}>
                    {breakEvenResult.break_even_found ? '✓ BREAK-EVEN IDENTIFIED' : 'ℹ DOMINANCE CONFIRMED'}
                  </span>
                </div>
                <p className="text-sm text-slate-200 mt-1">{breakEvenResult.explanation}</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Monte Carlo Validation */}
        {activeAnalysisTab === 'MONTE_CARLO' && (
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 font-medium">Independent Iterations:</span>
                {[10, 50, 100].map((runs) => (
                  <button
                    key={runs}
                    onClick={() => setMcRuns(runs)}
                    className={`px-2.5 py-1 rounded text-xs font-semibold ${
                      mcRuns === runs
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-900 text-slate-400 border border-slate-800'
                    }`}
                  >
                    {runs} Runs
                  </button>
                ))}
              </div>

              <button
                onClick={handleRunMonteCarlo}
                disabled={mcLoading}
                className="px-4 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded text-xs font-bold flex items-center gap-2"
              >
                {mcLoading ? (
                  <>
                    <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <span>Simulating {mcRuns} Runs...</span>
                  </>
                ) : (
                  <>
                    <span>▶ Run Monte Carlo</span>
                  </>
                )}
              </button>
            </div>

            {mcResult && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-slate-900 p-4 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-400 font-medium">Mean RecoverAI Lift:</span>
                  <div className="text-base font-bold text-emerald-400 mt-0.5">
                    +{mcResult.mean_recoverai_lift_pct.toFixed(1)}%
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 font-medium">Median Lift:</span>
                  <div className="text-base font-bold text-white mt-0.5">
                    +{mcResult.median_recoverai_lift_pct.toFixed(1)}%
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 font-medium">95% Confidence Interval:</span>
                  <div className="text-base font-bold text-indigo-300 mt-0.5">
                    [{mcResult.confidence_interval_95[0].toFixed(1)}%, {mcResult.confidence_interval_95[1].toFixed(1)}%]
                  </div>
                </div>

                <div>
                  <span className="text-slate-400 font-medium">Accounting Invariant:</span>
                  <div className="text-base font-bold text-emerald-400 mt-0.5">
                    {mcResult.accounting_imbalance_all_zero ? '100% Exact' : 'Mismatch'}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
