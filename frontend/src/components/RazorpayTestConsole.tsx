import React, { useState } from 'react';
import { testProviderConnection, createTestPaymentLink, fetchProviderPayment } from '../api';

interface RazorpayTestConsoleProps {
  providerMode: string;
  isVisible: boolean;
}

interface TestResult {
  label: string;
  success: boolean | null;
  message: string;
  detail?: any;
  timestamp?: string;
  loading?: boolean;
}

const ResultCard: React.FC<{ result: TestResult }> = ({ result }) => {
  const [expanded, setExpanded] = useState(false);

  const borderColor = result.loading ? '#1a73e8' : result.success ? '#34a853' : '#d93025';
  const bgColor = result.loading ? '#e8f0fe' : result.success ? '#e6f4ea' : '#fce8e6';
  const icon = result.loading ? '⟳' : result.success ? '✓' : '✗';

  return (
    <div style={{
      border: `1px solid ${borderColor}`,
      borderRadius: 8,
      padding: '10px 14px',
      marginBottom: 8,
      background: bgColor,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16, color: borderColor }}>{icon}</span>
          <span style={{ fontSize: 13, fontWeight: 600, color: '#3c4043' }}>{result.label}</span>
        </div>
        {result.detail && (
          <button onClick={() => setExpanded(!expanded)} style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 6, border: '1px solid #dadce0',
            background: '#fff', cursor: 'pointer', color: '#5f6368',
          }}>
            {expanded ? 'Hide' : 'Details'}
          </button>
        )}
      </div>
      <div style={{ fontSize: 12, color: '#3c4043', marginTop: 4, paddingLeft: 24 }}>
        {result.message}
      </div>
      {expanded && result.detail && (
        <pre style={{
          marginTop: 8, padding: 8, background: '#fff', borderRadius: 6, fontSize: 11,
          color: '#3c4043', maxHeight: 200, overflow: 'auto', border: '1px solid #e0e0e0',
        }}>
          {JSON.stringify(result.detail, null, 2)}
        </pre>
      )}
    </div>
  );
};

const RazorpayTestConsole: React.FC<RazorpayTestConsoleProps> = ({ providerMode, isVisible }) => {
  const [results, setResults] = useState<TestResult[]>([]);
  const [paymentId, setPaymentId] = useState('pay_test_demo001');
  const [amount, setAmount] = useState('500');

  const pushResult = (r: TestResult) => setResults(prev => [r, ...prev.slice(0, 9)]);
  const updateLastResult = (update: Partial<TestResult>) =>
    setResults(prev => [{ ...prev[0], ...update }, ...prev.slice(1)]);

  const handleTestConnection = async () => {
    pushResult({ label: 'API Connection Test', success: null, message: 'Connecting…', loading: true });
    try {
      const data = await testProviderConnection();
      updateLastResult({
        success: data.success,
        message: data.message,
        detail: data,
        timestamp: new Date().toISOString(),
        loading: false,
      });
    } catch (err: any) {
      updateLastResult({ success: false, message: String(err), loading: false });
    }
  };

  const handleCreatePaymentLink = async () => {
    if (!paymentId || !amount) return;
    const amtNum = parseFloat(amount);
    pushResult({ label: `Create Payment Link (${paymentId})`, success: null, message: 'Creating…', loading: true });
    try {
      const data = await createTestPaymentLink(paymentId, amtNum, 'RecoverAI Test Console');
      updateLastResult({
        success: data.success,
        message: data.message || (data.link_url ? `Link: ${data.link_url}` : 'Created'),
        detail: { ...data, live_money: false },
        timestamp: new Date().toISOString(),
        loading: false,
      });
    } catch (err: any) {
      updateLastResult({ success: false, message: String(err), loading: false });
    }
  };

  const handleFetchPayment = async () => {
    if (!paymentId) return;
    pushResult({ label: `Fetch Payment (${paymentId})`, success: null, message: 'Fetching…', loading: true });
    try {
      const data = await fetchProviderPayment(paymentId);
      updateLastResult({
        success: true,
        message: `Status: ${data.status || data.note} | ₹${(data.amount_inr || 0).toFixed(2)}`,
        detail: {
          ...data,
          verified_recovery: false,
          IMPORTANT: 'HTTP 200 ≠ VERIFIED_RECOVERY — independent RecoveryVerifier required',
        },
        timestamp: new Date().toISOString(),
        loading: false,
      });
    } catch (err: any) {
      updateLastResult({ success: false, message: String(err), loading: false });
    }
  };

  const loadRazorpayScript = () => {
    return new Promise((resolve) => {
      if ((window as any).Razorpay) return resolve(true);
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  const handleTestCheckout = async () => {
    if (!paymentId || !amount) return;
    const amtNum = parseFloat(amount);
    pushResult({ label: `Web Checkout (${paymentId})`, success: null, message: 'Creating order…', loading: true });
    
    try {
      // 1. Create order
      const { createCheckoutOrder, verifyCheckoutSignature } = await import('../api');
      const orderData = await createCheckoutOrder(paymentId, amtNum);
      
      if (!orderData.success) {
        throw new Error(orderData.message || 'Order creation failed');
      }

      updateLastResult({ success: true, message: `Order created: ${orderData.order_id}`, detail: orderData, loading: true });

      // 2. Load script
      const scriptLoaded = await loadRazorpayScript();
      if (!scriptLoaded) throw new Error('Razorpay SDK failed to load');

      // 3. Open checkout
      const options = {
        key: orderData.key_id || 'sim_key_id',
        amount: Math.round(orderData.amount * 100).toString(),
        currency: orderData.currency,
        name: 'RecoverAI Sandbox',
        description: `Test Checkout for ${paymentId}`,
        order_id: orderData.order_id,
        handler: async (response: any) => {
          updateLastResult({ success: true, message: 'Payment returned. Verifying...', detail: response, loading: true });
          // 4. Verify signature
          try {
            const verifyData = await verifyCheckoutSignature(
              response.razorpay_order_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            );
            updateLastResult({ 
              success: verifyData.success, 
              message: verifyData.message, 
              detail: { ...response, verified: verifyData.success }, 
              loading: false 
            });
          } catch (e: any) {
            updateLastResult({ success: false, message: `Verification failed: ${e}`, detail: response, loading: false });
          }
        },
        prefill: {
          name: 'Test User',
          email: 'test@recoverai.local',
          contact: '9999999999'
        },
        theme: { color: '#1a73e8' }
      };

      if (orderData.provider === 'mock') {
         updateLastResult({ success: true, message: 'Simulation checkout mocked.', loading: false });
         return;
      }

      const rzp1 = new (window as any).Razorpay(options);
      rzp1.on('payment.failed', (response: any) => {
         updateLastResult({ success: false, message: 'Payment failed at checkout', detail: response.error, loading: false });
      });
      rzp1.open();

    } catch (err: any) {
      updateLastResult({ success: false, message: String(err), loading: false });
    }
  };

  if (!isVisible) return null;

  const isTestMode = providerMode === 'razorpay_test';
  const modeNote = isTestMode
    ? '🟢 RAZORPAY TEST MODE — Real API calls, no live money'
    : '🔵 SIMULATION MODE — All actions are deterministic mocks';

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700, color: '#1d1d1f' }}>🧪 Provider Test Console</div>
          <div style={{ fontSize: 12, color: '#5f6368', marginTop: 4 }}>{modeNote}</div>
        </div>
        <div style={{
          background: '#fce8e6', border: '1px solid #f28b82', borderRadius: 8,
          padding: '4px 12px', fontSize: 11, fontWeight: 700, color: '#d93025',
        }}>
          🔒 LIVE MONEY: DISABLED
        </div>
      </div>

      {/* Safety Banner */}
      <div style={{
        background: '#e8f0fe',
        border: '1px solid #4285f4',
        borderRadius: 8,
        padding: '8px 12px',
        marginBottom: 16,
        fontSize: 12,
        color: '#1a73e8',
      }}>
        <strong>RecoverAI Architecture:</strong> Gateway actions flow through ActionExecutor → PolicyEngine → RecoveryFirewall → Gateway.
        HTTP 200 from provider ≠ VERIFIED_RECOVERY. Independent RecoveryVerifier evaluates ledger state.
      </div>

      {/* Input Fields */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 2, minWidth: 200 }}>
          <label style={{ fontSize: 11, color: '#5f6368', fontWeight: 600, display: 'block', marginBottom: 4 }}>PAYMENT ID</label>
          <input
            value={paymentId}
            onChange={e => setPaymentId(e.target.value)}
            style={{
              width: '100%', padding: '7px 10px', border: '1px solid #dadce0', borderRadius: 8,
              fontSize: 13, fontFamily: 'monospace', boxSizing: 'border-box',
            }}
            placeholder="pay_test_abc123"
          />
        </div>
        <div style={{ flex: 1, minWidth: 100 }}>
          <label style={{ fontSize: 11, color: '#5f6368', fontWeight: 600, display: 'block', marginBottom: 4 }}>AMOUNT (₹)</label>
          <input
            value={amount}
            onChange={e => setAmount(e.target.value)}
            type="number"
            min="1"
            style={{
              width: '100%', padding: '7px 10px', border: '1px solid #dadce0', borderRadius: 8,
              fontSize: 13, boxSizing: 'border-box',
            }}
            placeholder="500"
          />
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        <button onClick={handleTestConnection} style={{
          padding: '8px 16px', background: '#1a73e8', color: '#fff', border: 'none',
          borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
        }}>
          🔌 Test Connection
        </button>
        <button onClick={handleCreatePaymentLink} style={{
          padding: '8px 16px', background: '#137333', color: '#fff', border: 'none',
          borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
        }}>
          🔗 Create Payment Link
        </button>
        <button onClick={handleFetchPayment} style={{
          padding: '8px 16px', background: '#e37400', color: '#fff', border: 'none',
          borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
        }}>
          🔍 Fetch Payment
        </button>
        <button onClick={handleTestCheckout} style={{
          padding: '8px 16px', background: '#9334e6', color: '#fff', border: 'none',
          borderRadius: 8, cursor: 'pointer', fontSize: 13, fontWeight: 600,
        }}>
          🛒 Web Checkout
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: '#80868b', fontWeight: 600, textTransform: 'uppercase', marginBottom: 8 }}>
            Test Results (most recent first)
          </div>
          {results.map((r, i) => <ResultCard key={i} result={r} />)}
        </div>
      )}

      {results.length === 0 && (
        <div style={{
          border: '1px dashed #dadce0', borderRadius: 8, padding: 24,
          textAlign: 'center', color: '#80868b', fontSize: 13,
        }}>
          Run a test action above to see results here
        </div>
      )}
    </div>
  );
};

export default RazorpayTestConsole;
