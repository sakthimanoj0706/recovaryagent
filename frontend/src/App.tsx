import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { HeroMetrics } from './components/HeroMetrics';
import { SystemHealthPanel } from './components/SystemHealthPanel';
import { EventStreamPanel, TimelineEventItem } from './components/EventStreamPanel';
import { LivePipeline } from './components/LivePipeline';
import { FinancialTruthPanel } from './components/FinancialTruthPanel';
import { DecisionExplanationPanel } from './components/DecisionExplanationPanel';
import { FirewallPanel } from './components/FirewallPanel';
import { FlipFlopHighlight } from './components/FlipFlopHighlight';
import { ScenarioSimulator } from './components/ScenarioSimulator';
import { VerificationProofPanel } from './components/VerificationProofPanel';
import { AgentActivityStream } from './components/AgentActivityStream';
import { PaymentsExplorer } from './components/PaymentsExplorer';
import { AuditTrailModal } from './components/AuditTrailModal';
import { PaymentDetailPanel } from './components/PaymentDetailPanel';
import { BenchmarkPanel } from './components/BenchmarkPanel';
import { PolicyLab } from './components/PolicyLab';



import {
  fetchMetrics,
  fetchPayments,
  fetchAuditTrail,
  fetchEventTimeline,
  fetchSystemHealth,
  runDemoScenario,
  runRecovery,
  resetDemoState,
} from './api';
import { SystemMetrics, PaymentItem, ClosedLoopOutcome, PipelineStep, AuditEntry } from './types';

export const App: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [eventStream, setEventStream] = useState<TimelineEventItem[]>([]);
  const [payments, setPayments] = useState<PaymentItem[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [activeOutcome, setActiveOutcome] = useState<ClosedLoopOutcome | null>(null);
  const [timeline, setTimeline] = useState<PipelineStep[]>([]);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(-1);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | undefined>(undefined);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const loadInitialData = async () => {
    try {
      setIsLoading(true);
      const [m, p, a, h, e] = await Promise.allSettled([
        fetchMetrics(),
        fetchPayments(50, 0, 'ALL'),
        fetchAuditTrail(50),
        fetchSystemHealth(),
        fetchEventTimeline(20),
      ]);

      if (m.status === 'fulfilled') setMetrics(m.value);
      if (p.status === 'fulfilled') setPayments(p.value.payments);
      if (a.status === 'fulfilled') setAuditEntries(a.value);
      if (h.status === 'fulfilled') setSystemHealth(h.value);
      if (e.status === 'fulfilled') {
        const mappedEvents: TimelineEventItem[] = e.value.timeline.map((evt: any) => ({
          event_id: evt.event_id || 'evt_unknown',
          event: evt.event || 'unknown',
          payment_id: evt.payment_id || 'pay_unknown',
          order_id: evt.order_id,
          amount: evt.amount,
          financial_state: evt.financial_state || 'UNKNOWN',
          ts: evt.ts || new Date().toISOString(),
          is_duplicate: evt.is_duplicate,
        }));
        setEventStream(mappedEvents);
      }
    } catch (err) {
      console.error('Failed to load initial RecoverAI data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleResetDemo = async () => {
    try {
      setIsLoading(true);
      await resetDemoState();
      setActiveOutcome(null);
      setTimeline([]);
      setActiveStepIndex(-1);
      await loadInitialData();
    } catch (err) {
      console.error('Failed to reset demo state:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunScenario = async (scenarioId: string, customAmount?: number) => {
    setIsPipelineRunning(true);
    setActiveOutcome(null);
    setTimeline([]);
    setActiveStepIndex(0);

    try {
      const resp = await runDemoScenario(scenarioId, customAmount);
      const outcome = resp.outcome;
      setActiveOutcome(outcome);

      const mappedTimeline: PipelineStep[] = (resp.timeline || []).map((t: any) => ({
        step: t.step,
        status: t.status,
        timestamp: t.timestamp,
        message: t.message,
        details: t.details,
      }));
      setTimeline(mappedTimeline);

      // Fast, crisp animation for live demos
      for (let i = 0; i <= mappedTimeline.length; i++) {
        setActiveStepIndex(i);
        await new Promise((resolve) => setTimeout(resolve, 80));
      }

      await loadInitialData();
    } catch (err) {
      console.error('Error running scenario:', err);
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const handleRunPayment = async (paymentId: string) => {
    setIsPipelineRunning(true);
    try {
      const outcome = await runRecovery(paymentId);
      setActiveOutcome(outcome);
      await loadInitialData();
    } catch (err) {
      console.error('Error executing recovery:', err);
    } finally {
      setIsPipelineRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080b11] text-slate-100 flex flex-col selection:bg-cyan-500/30 font-sans">
      {/* Top Header */}
      <Header
        onRefresh={loadInitialData}
        onOpenAudit={() => setIsAuditModalOpen(true)}
        onResetDemo={handleResetDemo}
        isLoading={isLoading}
      />

      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Module Health Topology Bar */}
        <SystemHealthPanel health={systemHealth} onRefresh={loadInitialData} />

        {/* Hero KPI Metrics Grid */}
        <HeroMetrics metrics={metrics} />

        {/* Scenario Command Center */}
        <ScenarioSimulator onRunScenario={handleRunScenario} isRunning={isPipelineRunning} />

        {/* Live Recovery 9-Stage Pipeline */}
        <LivePipeline
          timeline={timeline}
          outcome={activeOutcome}
          isRunning={isPipelineRunning}
          activeStepIndex={activeStepIndex}
        />

        {/* Agent 6-Stage Decision Trace & Financial Truth Reconciliation */}
        {activeOutcome && (
          <>
            <AgentDecisionTrace outcome={activeOutcome} />
            <FinancialTruthPanel outcome={activeOutcome} />
          </>
        )}

        {/* Decision Explainability Panel & Model Math Breakdown */}
        <DecisionExplanationPanel outcome={activeOutcome} />

        {/* Recovery Firewall Rule Inventory & Active Highlighting */}
        <FirewallPanel outcome={activeOutcome} />

        {/* 5 Core Fintech Intelligence Showcase Cards */}
        <FlipFlopHighlight
          onRunScenario={handleRunScenario}
          isRunning={isPipelineRunning}
        />

        {/* Real-Time Event Stream & Webhook Ingestion Feed */}
        <EventStreamPanel
          events={eventStream}
          onRefresh={loadInitialData}
          isLoading={isLoading}
        />

        {/* Verification Proof & Agent Telemetry Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-6">
            <VerificationProofPanel outcome={activeOutcome} />
          </div>

          <div className="lg:col-span-5 space-y-6 flex flex-col">
            <AgentActivityStream outcome={activeOutcome} />
          </div>
        </div>

        {/* Economic Impact Benchmark & ROI Engine (Step 11) */}
        <BenchmarkPanel />

        {/* Recovery Policy Lab & What-If Economic Simulator (Step 12) */}
        <PolicyLab />

        {/* Payments Explorer Full Table */}

        <PaymentsExplorer
          payments={payments}
          onSelectPayment={(id) => setSelectedPaymentId(id)}
          onRunPayment={handleRunPayment}
          selectedPaymentId={selectedPaymentId}
          isLoading={isPipelineRunning}
        />

      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-4 px-6 text-center text-xs font-mono text-slate-500 bg-[#080b11]">
        RecoverAI — &ldquo;Prove the money. Prioritize the chase. Recover it.&rdquo; | Production Simulation
      </footer>

      {/* Audit Trail Modal */}
      <AuditTrailModal
        isOpen={isAuditModalOpen}
        onClose={() => setIsAuditModalOpen(false)}
        entries={auditEntries}
      />

      {/* Payment Detail Slide-Out Panel */}
      {selectedPaymentId && (
        <PaymentDetailPanel
          paymentId={selectedPaymentId}
          onClose={() => setSelectedPaymentId(undefined)}
          onRunRecovery={handleRunPayment}
          isRunning={isPipelineRunning}
        />
      )}
    </div>
  );
};

export default App;
