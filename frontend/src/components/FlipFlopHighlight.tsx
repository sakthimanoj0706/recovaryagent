import React, { useState } from 'react';
import {
  ShieldCheck,
  Play,
  ArrowRight,
  AlertTriangle,
  CheckCircle,
  ShieldAlert,
  Sparkles,
  Scale,
  RefreshCw,
  Lock,
  EyeOff,
  Clock,
  ShieldX,
} from 'lucide-react';

interface FlipFlopHighlightProps {
  onRunScenario: (scenarioId: string, customAmount?: number) => void;
  isRunning: boolean;
}

type TabType = 'case_a' | 'case_b' | 'case_c' | 'case_d' | 'case_e';

export const FlipFlopHighlight: React.FC<FlipFlopHighlightProps> = ({ onRunScenario, isRunning }) => {
  const [activeTab, setActiveTab] = useState<TabType>('case_a');

  return (
    <div className="glass-card rounded-2xl p-5 sm:p-6 border border-white/10 bg-gradient-to-br from-slate-900/90 via-slate-950/80 to-slate-900/90 relative overflow-hidden shadow-2xl space-y-4">
      {/* Top Header & Tab Navigation */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 uppercase tracking-wider">
              Adversarial Safety Showcases
            </span>
            <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
              ADVERSARIAL FINTECH CASES &amp; GUARDRAILS
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            5 adversarial stress-test cases proving why RecoverAI isolates financial truth from LLMs and protects merchant trust.
          </p>
        </div>

        {/* 5 Tab Buttons */}
        <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-950/80 rounded-xl border border-white/10 text-xs font-mono">
          <button
            onClick={() => setActiveTab('case_a')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeTab === 'case_a'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Case A: Failed ≠ Lost
          </button>
          <button
            onClick={() => setActiveTab('case_b')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeTab === 'case_b'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Case B: Hard Decline
          </button>
          <button
            onClick={() => setActiveTab('case_c')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeTab === 'case_c'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Case C: Verifier Rejection
          </button>
          <button
            onClick={() => setActiveTab('case_d')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeTab === 'case_d'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Case D: 4th Retry Block
          </button>
          <button
            onClick={() => setActiveTab('case_e')}
            className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
              activeTab === 'case_e'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Case E: Uncertain State
          </button>
        </div>
      </div>

      {/* Case A: FAILED -> AUTHORIZED -> CAPTURED */}
      {activeTab === 'case_a' && (
        <div className="space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-cyan-400 font-mono">
                  &ldquo;FAILED ≠ LOST&rdquo; (Late Auth Flip)
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                  STATE-RULE-001
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-3xl">
                Payment initially failed, but bank authorization cleared 45 minutes later. State Engine halts pursuit before calling the LLM planner, preventing a double charge.
              </p>
            </div>

            <button
              onClick={() => onRunScenario('2', 25000)}
              disabled={isRunning}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:from-cyan-400 hover:to-emerald-400 text-slate-950 font-bold text-xs tracking-wider uppercase font-mono shadow-lg shadow-cyan-500/25 transition-all disabled:opacity-50 shrink-0"
            >
              <Play className="w-4 h-4 fill-slate-950" />
              <span>Run Case A (₹25,000)</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30">
              <div className="text-[10px] text-rose-400 uppercase font-semibold">1. Webhook Ingest</div>
              <div className="text-sm font-bold text-white mt-1">payment.failed</div>
              <div className="text-[11px] text-slate-400 mt-1">Bank downtime timeout</div>
            </div>
            <div className="p-3.5 rounded-xl bg-indigo-950/20 border border-indigo-500/30">
              <div className="text-[10px] text-indigo-400 uppercase font-semibold">2. Ledger Proof</div>
              <div className="text-sm font-bold text-emerald-300 mt-1">ALREADY_RECOVERED</div>
              <div className="text-[11px] text-slate-400 mt-1">Late capture cleared</div>
            </div>
            <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30">
              <div className="text-[10px] text-amber-400 uppercase font-semibold">3. LLM Gate</div>
              <div className="text-sm font-bold text-amber-300 mt-1">NOT INVOKED</div>
              <div className="text-[11px] text-slate-400 mt-1">Bypasses advisory planner</div>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
              <div className="text-[10px] text-emerald-400 uppercase font-semibold">4. Final Protection</div>
              <div className="text-sm font-bold text-emerald-300 mt-1">₹25,000 Withheld</div>
              <div className="text-[11px] text-slate-400 mt-1">Zero duplicate charge</div>
            </div>
          </div>
        </div>
      )}

      {/* Case B: CARD_BLOCKED + Positive ENV */}
      {activeTab === 'case_b' && (
        <div className="space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-amber-400 font-mono">
                  &ldquo;ECONOMICS ≠ PERMISSION&rdquo; (Hard Decline)
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  FIREWALL-004
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-3xl">
                Amount is ₹12,000 with positive Expected Net Value (+₹1,632). Even if an LLM advisor recommends a retry, the deterministic Firewall enforces hard card network decline rules and blocks the action.
              </p>
            </div>

            <button
              onClick={() => onRunScenario('3', 12000)}
              disabled={isRunning}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-400 hover:to-rose-400 text-slate-950 font-bold text-xs tracking-wider uppercase font-mono shadow-lg shadow-amber-500/25 transition-all disabled:opacity-50 shrink-0"
            >
              <Play className="w-4 h-4 fill-slate-950" />
              <span>Run Case B (₹12,000)</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-white/10">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">1. Failure Code</div>
              <div className="text-sm font-bold text-rose-400 mt-1">CARD_BLOCKED</div>
              <div className="text-[11px] text-slate-400 mt-1">Hard network decline</div>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
              <div className="text-[10px] text-emerald-400 uppercase font-semibold">2. Unit Economics</div>
              <div className="text-sm font-bold text-emerald-300 mt-1">+₹1,632.43 ENV</div>
              <div className="text-[11px] text-slate-400 mt-1">P(success) = 14.3%</div>
            </div>
            <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30">
              <div className="text-[10px] text-rose-400 uppercase font-semibold">3. Firewall Verdict</div>
              <div className="text-sm font-bold text-rose-300 mt-1">FIREWALL-004 STOP</div>
              <div className="text-[11px] text-slate-400 mt-1">Gateway spam prohibited</div>
            </div>
            <div className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/30">
              <div className="text-[10px] text-cyan-400 uppercase font-semibold">4. Result</div>
              <div className="text-sm font-bold text-cyan-300 mt-1">₹12,000 Withheld</div>
              <div className="text-[11px] text-slate-400 mt-1">SAFE_STOP executed</div>
            </div>
          </div>
        </div>
      )}

      {/* Case C: Agent Recommends Success, Executor Fails */}
      {activeTab === 'case_c' && (
        <div className="space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-rose-400 font-mono">
                  &ldquo;AGENT CLAIM ≠ FINANCIAL TRUTH&rdquo; (Verification)
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/30">
                  RECOVERY VERIFIER
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-3xl">
                A Payment Link was generated and dispatched, but the customer abandoned checkout. Closed-loop verification re-evaluates the ledger, confirms money remains lost, and logs ₹0 recovered.
              </p>
            </div>

            <button
              onClick={() => onRunScenario('5', 15000)}
              disabled={isRunning}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-amber-500 hover:from-rose-400 hover:to-amber-400 text-slate-950 font-bold text-xs tracking-wider uppercase font-mono shadow-lg shadow-rose-500/25 transition-all disabled:opacity-50 shrink-0"
            >
              <Play className="w-4 h-4 fill-slate-950" />
              <span>Run Case C (₹15,000)</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/30">
              <div className="text-[10px] text-cyan-400 uppercase font-semibold">1. Agent Action</div>
              <div className="text-sm font-bold text-cyan-300 mt-1">PAYMENT_LINK</div>
              <div className="text-[11px] text-slate-400 mt-1">Dispatched to customer</div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-white/10">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">2. Execution</div>
              <div className="text-sm font-bold text-slate-200 mt-1">SIMULATED_FAILURE</div>
              <div className="text-[11px] text-slate-400 mt-1">Customer abandoned</div>
            </div>
            <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30">
              <div className="text-[10px] text-rose-400 uppercase font-semibold">3. State Engine Proof</div>
              <div className="text-sm font-bold text-rose-300 mt-1">VERIFIED_LOST</div>
              <div className="text-[11px] text-slate-400 mt-1">No capture recorded</div>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
              <div className="text-[10px] text-emerald-400 uppercase font-semibold">4. Verified Metric</div>
              <div className="text-sm font-bold text-emerald-300 mt-1">₹0.00 Claimed</div>
              <div className="text-[11px] text-slate-400 mt-1">Zero false recovery claims</div>
            </div>
          </div>
        </div>
      )}

      {/* Case D: 4th Retry Block (FIREWALL-005) */}
      {activeTab === 'case_d' && (
        <div className="space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-purple-400 font-mono">
                  &ldquo;RETRY CEILING PROTECTION&rdquo; (Attempt 4)
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30">
                  FIREWALL-005
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-3xl">
                Payment failed 3 consecutive times. On the 4th attempt, FIREWALL-005 halts execution to prevent gateway rate-limiting and merchant penalty fees.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-xl bg-purple-500/20 text-purple-300 text-xs font-bold border border-purple-500/30">
                MAX_RETRY_PROTECTION (3 Attempts Max)
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-white/10">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Attempts 1–3</div>
              <div className="text-sm font-bold text-slate-200 mt-1">3 Retries Failed</div>
              <div className="text-[11px] text-slate-400 mt-1">Soft timeout failures</div>
            </div>
            <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30">
              <div className="text-[10px] text-rose-400 uppercase font-semibold">Attempt 4</div>
              <div className="text-sm font-bold text-rose-300 mt-1">FIREWALL-005 STOP</div>
              <div className="text-[11px] text-slate-400 mt-1">Retry limit exceeded</div>
            </div>
            <div className="p-3.5 rounded-xl bg-purple-950/20 border border-purple-500/30">
              <div className="text-[10px] text-purple-400 uppercase font-semibold">Gateway Health</div>
              <div className="text-sm font-bold text-purple-300 mt-1">Spam Prevented</div>
              <div className="text-[11px] text-slate-400 mt-1">No penalty fees incurred</div>
            </div>
            <div className="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/30">
              <div className="text-[10px] text-cyan-400 uppercase font-semibold">Accounting</div>
              <div className="text-sm font-bold text-cyan-300 mt-1">₹4,500 Withheld</div>
              <div className="text-[11px] text-slate-400 mt-1">Safe stop logged</div>
            </div>
          </div>
        </div>
      )}

      {/* Case E: UNCERTAIN State (Awaiting Clearing) */}
      {activeTab === 'case_e' && (
        <div className="space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-emerald-400 font-mono">
                  &ldquo;UNCERTAIN IS NOT LOST&rdquo; (In-Flight Settlement)
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
                  STATE-RULE-004 / FIREWALL-007
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-3xl">
                Payment is currently pending within the bank settlement clearing window. State Engine assigns UNCERTAIN, and Firewall enforces WAIT.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-300 text-xs font-bold border border-amber-500/30">
                WAIT Status (₹6,000.00 Pending)
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30">
              <div className="text-[10px] text-amber-400 uppercase font-semibold">1. Status</div>
              <div className="text-sm font-bold text-amber-300 mt-1">payment.pending</div>
              <div className="text-[11px] text-slate-400 mt-1">In-flight banking queue</div>
            </div>
            <div className="p-3.5 rounded-xl bg-indigo-950/20 border border-indigo-500/30">
              <div className="text-[10px] text-indigo-400 uppercase font-semibold">2. State Rule</div>
              <div className="text-sm font-bold text-indigo-300 mt-1">STATE-RULE-004</div>
              <div className="text-[11px] text-slate-400 mt-1">Assigned UNCERTAIN</div>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/40 border border-white/10">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">3. Firewall Rule</div>
              <div className="text-sm font-bold text-slate-200 mt-1">FIREWALL-007 WAIT</div>
              <div className="text-[11px] text-slate-400 mt-1">Premature chase blocked</div>
            </div>
            <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-500/30">
              <div className="text-[10px] text-emerald-400 uppercase font-semibold">4. Accounting</div>
              <div className="text-sm font-bold text-amber-300 mt-1">₹6,000.00 Pending</div>
              <div className="text-[11px] text-slate-400 mt-1">Never mixed with withheld</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
