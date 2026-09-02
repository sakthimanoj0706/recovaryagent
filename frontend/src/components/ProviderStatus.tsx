import React, { useEffect, useState } from 'react';
import { fetchProviderStatus } from '../api';

interface ProviderCapabilities {
  create_payment_link: boolean;
  fetch_payment: boolean;
  fetch_order: boolean;
  receive_webhooks: boolean;
  verify_webhook_signature: boolean;
  live_money_execution: boolean;
}

interface ProviderStatusData {
  provider_mode: string;
  provider_name: string;
  test_mode: boolean;
  simulation_mode: boolean;
  live_enabled: boolean;
  live_execution_blocked: boolean;
  configuration_status: string;
  webhook_configured: boolean;
  capabilities: ProviderCapabilities;
  gateway_provider: string;
  is_simulation: boolean;
  key_configured: boolean;
}

const modeBadgeStyle = (mode: string): React.CSSProperties => {
  if (mode === 'razorpay_test') return { background: '#1a73e8', color: '#fff', padding: '3px 12px', borderRadius: 12, fontWeight: 700, fontSize: 12, letterSpacing: 0.5 };
  if (mode === 'razorpay_live') return { background: '#d93025', color: '#fff', padding: '3px 12px', borderRadius: 12, fontWeight: 700, fontSize: 12 };
  return { background: '#5f6368', color: '#fff', padding: '3px 12px', borderRadius: 12, fontWeight: 700, fontSize: 12 };
};

const CapabilityRow: React.FC<{ label: string; enabled: boolean; alwaysFalse?: boolean }> = ({ label, enabled, alwaysFalse }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
    <span style={{ fontSize: 13, color: '#3c4043' }}>{label}</span>
    {alwaysFalse ? (
      <span style={{ fontSize: 12, fontWeight: 700, color: '#d93025', background: '#fce8e6', padding: '2px 8px', borderRadius: 8 }}>🔒 DISABLED</span>
    ) : enabled ? (
      <span style={{ fontSize: 12, fontWeight: 700, color: '#137333', background: '#e6f4ea', padding: '2px 8px', borderRadius: 8 }}>✓ Enabled</span>
    ) : (
      <span style={{ fontSize: 12, color: '#80868b', background: '#f1f3f4', padding: '2px 8px', borderRadius: 8 }}>— N/A</span>
    )}
  </div>
);

const ProviderStatus: React.FC = () => {
  const [status, setStatus] = useState<ProviderStatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchProviderStatus();
      setStatus(data);
    } catch (err) {
      setError('Failed to load provider status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return (
    <div style={{ padding: 20, color: '#80868b', fontSize: 14 }}>⟳ Loading provider status…</div>
  );

  if (error || !status) return (
    <div style={{ padding: 20, color: '#d93025', fontSize: 14 }}>⚠ {error || 'No provider status'}</div>
  );

  const modeDisplay = {
    simulation: 'SIMULATION',
    razorpay_test: 'RAZORPAY TEST MODE',
    razorpay_live: 'RAZORPAY LIVE (BLOCKED)',
  }[status.provider_mode] || status.provider_mode.toUpperCase();

  const configColor = {
    CONFIGURED: '#137333',
    PARTIAL: '#e37400',
    NOT_CONFIGURED: '#d93025',
    SIMULATION_NO_CREDENTIALS_REQUIRED: '#5f6368',
  }[status.configuration_status] || '#5f6368';

  return (
    <div style={{
      background: '#fff',
      border: '1px solid #dadce0',
      borderRadius: 12,
      padding: 20,
      marginBottom: 16,
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1d1d1f', marginBottom: 4 }}>
            💳 Payment Provider
          </div>
          <div style={{ fontSize: 13, color: '#5f6368' }}>
            {status.provider_name}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={modeBadgeStyle(status.provider_mode)}>{modeDisplay}</span>
        </div>
      </div>

      {/* Live Execution Banner — ALWAYS VISIBLE */}
      <div style={{
        background: '#fce8e6',
        border: '1px solid #f28b82',
        borderRadius: 8,
        padding: '8px 12px',
        marginBottom: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <span style={{ fontSize: 16 }}>🔒</span>
        <div>
          <div style={{ fontWeight: 700, fontSize: 13, color: '#d93025' }}>LIVE PAYMENT EXECUTION IS DISABLED</div>
          <div style={{ fontSize: 12, color: '#c5221f', marginTop: 2 }}>
            RecoverAI operates in bounded financial safety mode. No real money movement.
          </div>
        </div>
      </div>

      {/* Configuration Status */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        <div style={{ flex: 1, minWidth: 120, background: '#f8f9fa', borderRadius: 8, padding: '8px 12px' }}>
          <div style={{ fontSize: 11, color: '#80868b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Config Status</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: configColor }}>{status.configuration_status.replace(/_/g, ' ')}</div>
        </div>
        <div style={{ flex: 1, minWidth: 120, background: '#f8f9fa', borderRadius: 8, padding: '8px 12px' }}>
          <div style={{ fontSize: 11, color: '#80868b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>Webhook Signature</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: status.webhook_configured ? '#137333' : '#e37400' }}>
            {status.webhook_configured ? '✓ Configured' : '⚠ Not Configured'}
          </div>
        </div>
        <div style={{ flex: 1, minWidth: 120, background: '#f8f9fa', borderRadius: 8, padding: '8px 12px' }}>
          <div style={{ fontSize: 11, color: '#80868b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 4 }}>API Keys</div>
          <div style={{ fontSize: 13, fontWeight: 700, color: status.key_configured ? '#137333' : '#e37400' }}>
            {status.key_configured ? '✓ Set' : '⚠ Not Set'}
          </div>
        </div>
      </div>

      {/* Capabilities */}
      <div style={{ marginTop: 8 }}>
        <div style={{ fontSize: 12, color: '#80868b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>Capabilities</div>
        {status.capabilities && (
          <>
            <CapabilityRow label="Create Payment Link" enabled={status.capabilities.create_payment_link} />
            <CapabilityRow label="Fetch Payment Status" enabled={status.capabilities.fetch_payment} />
            <CapabilityRow label="Fetch Order" enabled={status.capabilities.fetch_order} />
            <CapabilityRow label="Receive Webhooks" enabled={status.capabilities.receive_webhooks} />
            <CapabilityRow label="Webhook Signature Verification" enabled={status.capabilities.verify_webhook_signature} />
            <CapabilityRow label="Live Money Execution" enabled={false} alwaysFalse={true} />
          </>
        )}
      </div>

      <button onClick={load} style={{
        marginTop: 12, padding: '6px 16px', fontSize: 12, border: '1px solid #dadce0',
        borderRadius: 8, background: '#fff', color: '#1a73e8', cursor: 'pointer', fontWeight: 600,
      }}>
        ↻ Refresh
      </button>
    </div>
  );
};

export default ProviderStatus;
