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



