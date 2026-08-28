import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { HeroMetrics } from './components/HeroMetrics';
import { SystemHealthPanel } from './components/SystemHealthPanel';
import { EventStreamPanel, TimelineEventItem } from './components/EventStreamPanel';
import { LivePipeline } from './components/LivePipeline';
import { WhyDidWeActPanel } from './components/WhyDidWeActPanel';
import { VerificationProofPanel } from './components/VerificationProofPanel';
import { FlipFlopHighlight } from './components/FlipFlopHighlight';
import { ScenarioSimulator } from './components/ScenarioSimulator';
import { FirewallView } from './components/FirewallView';
import { AgentActivityStream } from './components/AgentActivityStream';
import { PaymentsExplorer } from './components/PaymentsExplorer';
import { AuditTrailModal } from './components/AuditTrailModal';
import { PaymentDetailPanel } from './components/PaymentDetailPanel';
import { AgentDecisionTrace } from './components/AgentDecisionTrace';

import {
  fetchMetrics,
  fetchPayments,
  fetchAuditTrail,
  fetchEventTimeline,
  fetchSystemHealth,
  runDemoScenario,
  runRecovery,
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
  const [isLoading, setIsLoading] = useState(false);
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [selectedPaymentId, setSelectedPaymentId] = useState<string | undefined>(undefined);

  // Load initial data
  const loadInitialData = async () => {
    setIsLoading(true);
    try {
      const [m, p, a, h, ev] = await Promise.all([
        fetchMetrics().catch(() => null),
        fetchPayments(50, 0, 'ALL').catch(() => ({ total: 0, payments: [] })),
        fetchAuditTrail(50).catch(() => []),
        fetchSystemHealth().catch(() => null),
        fetchEventTimeline(30).catch(() => ({ total_events: 0, timeline: [] })),
      ]);
      if (m) setMetrics(m);
      if (p.payments) setPayments(p.payments);
      if (a) setAuditEntries(a);
      if (h) setSystemHealth(h);
      if (ev && ev.timeline) setEventStream(ev.timeline);
    } catch (err) {
      console.error('Failed to load initial data', err);
    } finally {
      setIsLoading(false);
    }
  };


  useEffect(() => {
    loadInitialData();
  }, []);

  // Animate through pipeline stages smoothly
  const animatePipeline = async (demoTimeline: PipelineStep[], finalOutcome: ClosedLoopOutcome) => {
    setIsPipelineRunning(true);
    setActiveOutcome(null);
    setTimeline(demoTimeline);

    for (let i = 0; i < demoTimeline.length; i++) {
      setActiveStepIndex(i);
      // Stagger animation timing for realistic feel
      await new Promise((resolve) => setTimeout(resolve, 350));
    }

    setActiveStepIndex(demoTimeline.length);
    setActiveOutcome(finalOutcome);
    setIsPipelineRunning(false);

    // Refresh metrics and audit log in background
    const [m, a] = await Promise.all([
      fetchMetrics().catch(() => null),
      fetchAuditTrail(50).catch(() => []),
    ]);
    if (m) setMetrics(m);
    if (a) setAuditEntries(a);
  };

  // Run Scenario from Simulator
  const handleRunScenario = async (scenarioId: string, customAmount?: number) => {
    try {
      setIsLoading(true);
      const res = await runDemoScenario(scenarioId, customAmount);
      setSelectedPaymentId(res.outcome.payment_id);
      await animatePipeline(res.timeline, res.outcome);
    } catch (err) {
      console.error('Error running scenario', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Run specific payment from list
  const handleRunPayment = async (paymentId: string) => {
    try {
      setIsLoading(true);
      const res = await runRecovery(paymentId);
      setSelectedPaymentId(paymentId);

      // Build synthetic timeline for this payment
      const pTimeline: PipelineStep[] = [
        { step: 'PAYMENT', status: 'COMPLETED', label: 'Payment Ingested', detail: `ID: ${res.payment_id}` },
        { step: 'PROVE', status: 'COMPLETED', label: 'Financial State', detail: res.initial_state },
        { step: 'PRIORITIZE', status: 'COMPLETED', label: 'Recovery Intel', detail: `ENV: ₹${res.expected_net_value || 0}` },
        { step: 'AGENT', status: 'COMPLETED', label: 'Agent Planner', detail: res.agent_action || 'STOP' },
        { step: 'FIREWALL', status: 'COMPLETED', label: 'Firewall', detail: res.firewall_decision },
        { step: 'ACT', status: 'COMPLETED', label: 'Execution', detail: res.execution_status },
        { step: 'VERIFY', status: 'COMPLETED', label: 'Verified Result', detail: res.verification_state },
      ];

      await animatePipeline(pTimeline, res);
    } catch (err) {
      console.error('Error running recovery on payment', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080b11] text-slate-100 flex flex-col font-sans">
      <Header
        onRefresh={loadInitialData}
        onOpenAudit={() => setIsAuditModalOpen(true)}
        isLoading={isLoading}
      />

      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Top Hero KPI Cards */}
        <HeroMetrics metrics={metrics} />

        {/* System Health & Module Topology Bar (Step 6) */}
        <SystemHealthPanel health={systemHealth} />

        {/* 5 Scenario Quick Trigger Bar */}
        <ScenarioSimulator onRunScenario={handleRunScenario} isRunning={isPipelineRunning} />

        {/* Live Recovery Pipeline */}
        <LivePipeline
          timeline={timeline}
          outcome={activeOutcome}
          isRunning={isPipelineRunning}
          activeStepIndex={activeStepIndex}
        />

        {/* Agent 6-Stage Decision Trace & Safety Proof */}
        {activeOutcome && (
          <AgentDecisionTrace outcome={activeOutcome} />
        )}

        {/* 5 Core Fintech Intelligence Showcase Cards */}
        <FlipFlopHighlight
          onRunScenario={handleRunScenario}
          isRunning={isPipelineRunning}
        />

        {/* Real-Time Event Stream & Webhook Ingestion Feed (Step 6) */}
        <EventStreamPanel
          events={eventStream}
          onRefresh={loadInitialData}
          isLoading={isLoading}
        />

        {/* Explainability Matrix & Verification Proof Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-6">
            {/* Most Important Section: Why Did RecoverAI Act? */}
            <WhyDidWeActPanel outcome={activeOutcome} />
            {/* Verification Proof Panel: Agent Claim vs Truth */}
            <VerificationProofPanel outcome={activeOutcome} />
          </div>

          <div className="lg:col-span-5 space-y-6 flex flex-col">
            {/* Agent Structured Activity Telemetry */}
            <AgentActivityStream outcome={activeOutcome} />
            {/* Firewall Policies View */}
            <FirewallView />
          </div>
        </div>

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
