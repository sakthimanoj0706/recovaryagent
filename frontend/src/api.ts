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

