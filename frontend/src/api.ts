import { SystemMetrics, PaymentItem, DemoScenarioResponse, AuditEntry } from './types';

const API_BASE = '/api';

export async function fetchMetrics(): Promise<SystemMetrics> {
  const res = await fetch(`${API_BASE}/metrics`);
  if (!res.ok) throw new Error('Failed to fetch metrics');
  return res.json();
}

export async function fetchPayments(limit = 50, offset = 0, filterState = 'ALL'): Promise<{ total: number; payments: PaymentItem[] }> {
  const res = await fetch(`${API_BASE}/payments?limit=${limit}&offset=${offset}&filter_state=${filterState}`);
  if (!res.ok) throw new Error('Failed to fetch payments');
  return res.json();
}

export async function fetchPaymentDetails(paymentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/payments/${paymentId}`);
  if (!res.ok) throw new Error(`Failed to fetch payment ${paymentId}`);
  return res.json();
}

export async function runRecovery(paymentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/recovery/run/${paymentId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to run recovery on ${paymentId}`);
  return res.json();
}

export async function runDemoScenario(scenarioId: string, customAmount?: number): Promise<DemoScenarioResponse> {
  const res = await fetch(`${API_BASE}/demo/${scenarioId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenario_id: scenarioId, custom_amount: customAmount }),
  });
  if (!res.ok) throw new Error(`Failed to run demo scenario ${scenarioId}`);
  return res.json();
}

export async function fetchAuditTrail(limit = 50): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/audit?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch audit log');
  return res.json();
}

export async function fetchRecoveryTrace(paymentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/recovery/${paymentId}/trace`);
  if (!res.ok) throw new Error(`Failed to fetch trace for ${paymentId}`);
  return res.json();
}

export async function fetchEventTimeline(limit = 50): Promise<{ total_events: number; timeline: any[] }> {
  const res = await fetch(`${API_BASE}/events/timeline?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch event timeline');
  return res.json();
}

export async function fetchSystemHealth(): Promise<any> {
  const res = await fetch(`${API_BASE}/system/health`);
  if (!res.ok) throw new Error('Failed to fetch system health');
  return res.json();
}

export async function resetDemoState(): Promise<any> {
  const res = await fetch(`${API_BASE}/demo/reset`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reset demo state');
  return res.json();
}


export async function postPaymentWebhook(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/webhooks/payment`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to submit webhook');
  return res.json();
}

export async function runBenchmark(payments = 1000, seed = 42): Promise<any> {
  const res = await fetch(`${API_BASE}/benchmark/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payments, seed }),
  });
  if (!res.ok) throw new Error('Failed to run benchmark');
  return res.json();
}

export async function fetchLatestBenchmark(): Promise<any> {
  const res = await fetch(`${API_BASE}/benchmark/latest`);
  if (!res.ok) throw new Error('Failed to fetch latest benchmark');
  return res.json();
}

export async function fetchBenchmarkCompare(): Promise<any> {
  const res = await fetch(`${API_BASE}/benchmark/compare`);
  if (!res.ok) throw new Error('Failed to fetch benchmark comparison');
  return res.json();
}

// =========================================================================
// POLICY LAB APIS (STEP 12)
// =========================================================================
export async function runPolicyLab(env?: any, custom_policy?: any): Promise<any> {
  const res = await fetch(`${API_BASE}/policy-lab/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ env, custom_policy }),
  });
  if (!res.ok) throw new Error('Failed to run Policy Lab simulation');
  return res.json();
}

export async function fetchLatestPolicyLab(): Promise<any> {
  const res = await fetch(`${API_BASE}/policy-lab/latest`);
  if (!res.ok) throw new Error('Failed to fetch latest Policy Lab run');
  return res.json();
}

export async function runPolicySensitivity(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/policy-lab/sensitivity`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to run sensitivity analysis');
  return res.json();
}

export async function runPolicyBreakEven(payload: any): Promise<any> {
  const res = await fetch(`${API_BASE}/policy-lab/break-even`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to run break-even analysis');
  return res.json();
}

export async function runPolicyMonteCarlo(config: any): Promise<any> {
  const res = await fetch(`${API_BASE}/policy-lab/monte-carlo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error('Failed to run Monte Carlo simulation');
  return res.json();
}

// =========================================================================
// RECOVERY DECISION REPLAY APIS (STEP 13)
// =========================================================================
export async function fetchReplayPresets(): Promise<any> {
  const res = await fetch(`${API_BASE}/replay/presets`);
  if (!res.ok) throw new Error('Failed to fetch replay presets');
  return res.json();
}

export async function fetchLatestReplay(): Promise<any> {
  const res = await fetch(`${API_BASE}/replay/latest`);
  if (!res.ok) throw new Error('Failed to fetch latest decision replay');
  return res.json();
}

export async function runDecisionReplay(preset_key?: string, payment?: any, events?: any): Promise<any> {
  const res = await fetch(`${API_BASE}/replay/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preset_key, payment, events, simulation_only: true }),
  });
  if (!res.ok) throw new Error('Failed to run decision replay');
  return res.json();
}

export async function fetchReplayGraph(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/replay/${runId}/graph`);
  if (!res.ok) throw new Error('Failed to fetch replay graph');
  return res.json();
}

export async function fetchReplayExplanation(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/replay/${runId}/explanation`);
  if (!res.ok) throw new Error('Failed to fetch replay explanation');
  return res.json();
}

export async function fetchReplayEvidence(runId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/replay/${runId}/evidence`);
  if (!res.ok) throw new Error('Failed to fetch replay evidence');
  return res.json();
}

// =============================================================================
// Step 14: Provider Status & Razorpay Test Console API
// =============================================================================

export async function fetchProviderStatus(): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/status`);
  if (!res.ok) throw new Error('Failed to fetch provider status');
  return res.json();
}

export async function testProviderConnection(): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/test-connection`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Provider connection test failed');
  return res.json();
}

export async function createTestPaymentLink(paymentId: string, amount: number, description?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/payment-link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payment_id: paymentId, amount, description }),
  });
  if (!res.ok) throw new Error('Failed to create payment link');
  return res.json();
}

export async function fetchProviderPayment(paymentId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/payment/${paymentId}`);
  if (!res.ok) throw new Error(`Failed to fetch provider payment ${paymentId}`);
  return res.json();
}

export async function fetchProviderOrder(orderId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/order/${orderId}`);
  if (!res.ok) throw new Error(`Failed to fetch provider order ${orderId}`);
  return res.json();
}

export async function createCheckoutOrder(paymentId: string, amount: number): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/checkout/order`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payment_id: paymentId, amount }),
  });
  if (!res.ok) throw new Error('Failed to create checkout order');
  return res.json();
}

export async function verifyCheckoutSignature(orderId: string, paymentId: string, signature: string): Promise<any> {
  const res = await fetch(`${API_BASE}/provider/checkout/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      razorpay_order_id: orderId,
      razorpay_payment_id: paymentId,
      razorpay_signature: signature
    }),
  });
  if (!res.ok) throw new Error('Failed to verify checkout signature');
  return res.json();
}
