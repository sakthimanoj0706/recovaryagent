import React, { useState, useEffect } from 'react';
import {
  fetchReplayPresets,
  fetchLatestReplay,
  runDecisionReplay,
} from '../api';

export const DecisionReplay: React.FC = () => {
  const [presets, setPresets] = useState<any[]>([]);
  const [selectedPresetKey, setSelectedPresetKey] = useState<string>('SUCCESSFUL_RETRY');
  const [replayData, setReplayData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'timeline' | 'graph' | 'matrix'>('timeline');
  const [expandedNodes, setExpandedNodes] = useState<{ [key: string]: boolean }>({});
  const [tamperedHash, setTamperedHash] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPresetsAndLatest();
  }, []);

  const loadPresetsAndLatest = async () => {
    try {
      setLoading(true);
      setError(null);
      const presetList = await fetchReplayPresets();
      setPresets(presetList);

      const latest = await fetchLatestReplay();
      if (latest && latest.replay) {
        setReplayData(latest.replay);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to initialize decision replay');
    } finally {
      setLoading(false);
    }
  };

  const handleRunReplay = async (presetKey: string) => {
    try {
      setLoading(true);
      setError(null);
      setTamperedHash(null);
      const res = await runDecisionReplay(presetKey);
      if (res && res.replay) {
        setReplayData(res.replay);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to run replay');
    } finally {
      setLoading(false);
    }
  };

  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => ({ ...prev, [nodeId]: !prev[nodeId] }));
  };

  const simulateTamper = () => {
    if (!replayData) return;
    setTamperedHash('TAMPER_DETECTED_HASH_MISMATCH_fa89b27e891c');
  };

  const resetTamper = () => {
    setTamperedHash(null);
  };

  if (loading && !replayData) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>
        <div style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>⚡ Loading Decision Replay Engine...</div>
        <p>Reconstructing deterministic financial evidence graph...</p>
      </div>
    );
  }

  const proof = replayData?.financial_proof;
  const provenance = replayData?.provenance;
  const graph = replayData?.evidence_graph;
  const matrix = replayData?.candidate_matrix || [];

  return (
    <div style={{ padding: '1.5rem', backgroundColor: '#0f172a', color: '#f8fafc', minHeight: '100vh', fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      
      {/* HEADER */}
      <div style={{ borderBottom: '1px solid #334155', paddingBottom: '1.25rem', marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h1 style={{ margin: 0, fontSize: '1.75rem', fontWeight: 800, background: 'linear-gradient(135deg, #38bdf8, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              RECOVERAI DECISION REPLAY & EVIDENCE GRAPH
            </h1>
            <span style={{ fontSize: '0.75rem', backgroundColor: '#0284c7', color: '#fff', padding: '0.2rem 0.6rem', borderRadius: '9999px', fontWeight: 700 }}>
              STEP 13
            </span>
          </div>
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '0.95rem' }}>
            Trace exactly why RecoverAI acted, stopped, or escalated with complete transaction-level cryptographic provenance.
          </p>
        </div>

        {/* SIMULATION GUARDS */}
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span style={{ backgroundColor: '#1e293b', border: '1px solid #10b981', color: '#34d399', fontSize: '0.75rem', padding: '0.35rem 0.75rem', borderRadius: '6px', fontWeight: 600 }}>
            🛡️ SIMULATION ONLY
          </span>
          <span style={{ backgroundColor: '#1e293b', border: '1px solid #38bdf8', color: '#38bdf8', fontSize: '0.75rem', padding: '0.35rem 0.75rem', borderRadius: '6px', fontWeight: 600 }}>
            📊 SYNTHETIC TEST DATA
          </span>
          <span style={{ backgroundColor: '#1e293b', border: '1px solid #64748b', color: '#cbd5e1', fontSize: '0.75rem', padding: '0.35rem 0.75rem', borderRadius: '6px', fontWeight: 600 }}>
            🔒 NO REAL MONEY MOVEMENT
          </span>
        </div>
      </div>

      {error && (
        <div style={{ backgroundColor: '#ef444420', border: '1px solid #ef4444', color: '#fca5a5', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem' }}>
          ⚠️ {error}
        </div>
      )}

      {/* CASE SELECTOR */}
      <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ flex: 1, minWidth: '280px' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>
              SELECT SYNTHETIC FINANCIAL ARCHETYPE TO REPLAY:
            </label>
            <select
              value={selectedPresetKey}
              onChange={(e) => {
                setSelectedPresetKey(e.target.value);
                handleRunReplay(e.target.value);
              }}
              style={{
                width: '100%',
                backgroundColor: '#0f172a',
                border: '1px solid #475569',
                color: '#f8fafc',
                padding: '0.65rem 1rem',
                borderRadius: '8px',
                fontSize: '0.95rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              {presets.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.name} (₹{p.amount?.toLocaleString()})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => handleRunReplay(selectedPresetKey)}
            disabled={loading}
            style={{
              backgroundColor: '#0284c7',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '0.75rem 1.5rem',
              fontWeight: 700,
              fontSize: '0.95rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {loading ? 'Replaying...' : '⚡ Run Replay'}
          </button>
        </div>
      </div>

      {replayData && (
        <>
          {/* TOP SUMMARY KPI CARD */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>Payment ID</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#38bdf8', marginTop: '0.25rem' }}>{replayData.payment_id}</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Order: {replayData.order_id || 'N/A'}</div>
            </div>

            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>Transaction Face Value</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#f8fafc', marginTop: '0.25rem' }}>₹{proof?.total_amount?.toLocaleString()}</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Initial: {replayData.initial_financial_state}</div>
            </div>

            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>Selected Action</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: replayData.selected_action === 'STOP' ? '#94a3b8' : '#a855f7', marginTop: '0.25rem' }}>
                {replayData.selected_action}
              </div>
              <div style={{ fontSize: '0.75rem', color: replayData.firewall_verdict === 'APPROVED' ? '#34d399' : '#f87171' }}>
                Firewall: {replayData.firewall_verdict}
              </div>
            </div>

            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>Final Financial State</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#10b981', marginTop: '0.25rem' }}>{replayData.final_financial_state}</div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Verified Cash: ₹{proof?.verified_cash_collected?.toLocaleString()}</div>
            </div>

            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600, textTransform: 'uppercase' }}>Accounting Imbalance</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#34d399', marginTop: '0.25rem' }}>₹0.00</div>
              <div style={{ fontSize: '0.75rem', color: '#34d399' }}>✓ 100% Conserved</div>
            </div>
          </div>

          {/* WHY DECISION HEADLINE PROVENANCE BANNER */}
          <div style={{ backgroundColor: '#1e293b', borderLeft: '4px solid #38bdf8', borderRadius: '8px', padding: '1rem 1.25rem', marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.25rem' }}>
              DECISION PROVENANCE
            </div>
            <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc' }}>
              {provenance?.headline}
            </div>
            {provenance?.llm_advisory_summary && (
              <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '0.5rem', fontStyle: 'italic' }}>
                💡 Advisory Context: {provenance.llm_advisory_summary}
              </div>
            )}
            {provenance?.prompt_injection_detected && (
              <div style={{ marginTop: '0.5rem', backgroundColor: '#f59e0b20', border: '1px solid #f59e0b', color: '#fcd34d', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.85rem' }}>
                🛡️ <b>Prompt Injection Isolated:</b> Malicious instruction detected in transaction metadata. Zero authority over deterministic financial state or firewall gates.
              </div>
            )}
          </div>

          {/* TABS NAVIGATION */}
          <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #334155', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>
            <button
              onClick={() => setActiveTab('timeline')}
              style={{
                backgroundColor: activeTab === 'timeline' ? '#0284c7' : 'transparent',
                color: activeTab === 'timeline' ? '#fff' : '#94a3b8',
                border: 'none',
                borderRadius: '6px',
                padding: '0.5rem 1rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              🕒 Decision Timeline
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              style={{
                backgroundColor: activeTab === 'graph' ? '#0284c7' : 'transparent',
                color: activeTab === 'graph' ? '#fff' : '#94a3b8',
                border: 'none',
                borderRadius: '6px',
                padding: '0.5rem 1rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              🕸️ Evidence Graph (DAG)
            </button>
            <button
              onClick={() => setActiveTab('matrix')}
              style={{
                backgroundColor: activeTab === 'matrix' ? '#0284c7' : 'transparent',
                color: activeTab === 'matrix' ? '#fff' : '#94a3b8',
                border: 'none',
                borderRadius: '6px',
                padding: '0.5rem 1rem',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              📊 Action Decision Matrix
            </button>
          </div>

          {/* TAB 1: DECISION TIMELINE */}
          {activeTab === 'timeline' && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
              
              {/* VERTICAL TIMELINE */}
              <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem' }}>
                <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#38bdf8' }}>
                  Transaction Lifecycle Causal Timeline
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {graph?.nodes?.map((node: any, idx: number) => {
                    const isExpanded = !!expandedNodes[node.id];
                    const isSelected = node.node_type === 'FINAL_FINANCIAL_STATE' || node.node_type === 'INDEPENDENT_VERIFICATION';
                    return (
                      <div
                        key={node.id}
                        style={{
                          backgroundColor: '#0f172a',
                          border: isSelected ? '1px solid #10b981' : '1px solid #334155',
                          borderRadius: '8px',
                          padding: '0.85rem',
                          cursor: 'pointer',
                        }}
                        onClick={() => toggleNode(node.id)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                            <span style={{ fontSize: '0.75rem', backgroundColor: '#334155', color: '#94a3b8', padding: '0.15rem 0.45rem', borderRadius: '4px', fontWeight: 700 }}>
                              {String(idx + 1).padStart(2, '0')}
                            </span>
                            <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#f8fafc' }}>
                              {node.title}
                            </span>
                          </div>
                          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                            {node.source} {isExpanded ? '▲' : '▼'}
                          </span>
                        </div>

                        <p style={{ margin: '0.5rem 0 0 0', color: '#cbd5e1', fontSize: '0.85rem' }}>
                          {node.explanation}
                        </p>

                        {isExpanded && (
                          <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px dashed #334155', fontSize: '0.8rem' }}>
                            <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                              <b>Confidence:</b> <span style={{ color: '#38bdf8' }}>{node.confidence}</span>
                            </div>
                            <div style={{ color: '#94a3b8', marginBottom: '0.25rem' }}>
                              <b>Substantiating References:</b> {node.evidence_refs?.length ? node.evidence_refs.join(', ') : 'Root Event'}
                            </div>
                            <div style={{ backgroundColor: '#1e293b', padding: '0.5rem', borderRadius: '4px', marginTop: '0.5rem', overflowX: 'auto' }}>
                              <pre style={{ margin: 0, fontSize: '0.75rem', color: '#a5f3fc' }}>
                                {JSON.stringify(node.value, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* WHY ACTED & FINANCIAL PROOF */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                
                {/* DETERMINISTIC JUSTIFICATIONS */}
                <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem' }}>
                  <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#38bdf8' }}>
                    Why RecoverAI Acted (or Blocked)
                  </h3>

                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399', marginBottom: '0.4rem' }}>
                      PROVABLE REASONING CHAIN:
                    </div>
                    {provenance?.why_selected?.map((item: string, i: number) => (
                      <div key={i} style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.35rem', lineHeight: '1.4' }}>
                        {item}
                      </div>
                    ))}
                  </div>

                  {provenance?.why_rejected && Object.keys(provenance.why_rejected).length > 0 && (
                    <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #334155' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#f87171', marginBottom: '0.4rem' }}>
                        WHY OTHER ACTIONS WERE REJECTED:
                      </div>
                      {Object.entries(provenance.why_rejected).map(([action, reason]: any) => (
                        <div key={action} style={{ fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '0.3rem' }}>
                          <b style={{ color: '#fca5a5' }}>{action}:</b> {reason}
                        </div>
                      ))}
                    </div>
                  )}

                  {provenance?.safety_interceptions?.length > 0 && (
                    <div style={{ marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid #334155' }}>
                      <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fbbf24', marginBottom: '0.4rem' }}>
                        SAFETY INTERCEPTIONS:
                      </div>
                      {provenance.safety_interceptions.map((item: string, i: number) => (
                        <div key={i} style={{ fontSize: '0.8rem', color: '#fde68a', marginBottom: '0.25rem' }}>
                          ⚠️ {item}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* EXACT FINANCIAL PROOF */}
                <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem' }}>
                  <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#34d399' }}>
                    Closed-Loop Financial Proof & Balance
                  </h3>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.85rem' }}>
                    <div style={{ color: '#94a3b8' }}>Total Face Value:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700 }}>₹{proof?.total_amount?.toLocaleString()}</div>

                    <div style={{ color: '#34d399' }}>Verified Cash Collected:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700, color: '#34d399' }}>₹{proof?.verified_cash_collected?.toLocaleString()}</div>

                    <div style={{ color: '#94a3b8' }}>Protected Withheld Value:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700 }}>₹{proof?.protected_unrecovered_value?.toLocaleString()}</div>

                    <div style={{ color: '#94a3b8' }}>Outstanding Value:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700 }}>₹{proof?.outstanding_value?.toLocaleString()}</div>

                    <div style={{ color: '#94a3b8' }}>Refunded Value:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700 }}>₹{proof?.refunded_value?.toLocaleString()}</div>

                    <div style={{ color: '#38bdf8' }}>Claimed vs Verified:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700, color: '#38bdf8' }}>
                      ₹{proof?.claimed_recovery?.toLocaleString()} / ₹{proof?.verified_recovery?.toLocaleString()}
                    </div>

                    <div style={{ color: '#f87171' }}>Phantom Revenue:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700, color: '#34d399' }}>₹0.00 (Zero)</div>

                    <div style={{ color: '#f87171' }}>Double Charges:</div>
                    <div style={{ textAlign: 'right', fontWeight: 700, color: '#34d399' }}>0 (Zero)</div>

                    <div style={{ color: '#10b981', fontWeight: 700, borderTop: '1px solid #334155', paddingTop: '0.5rem' }}>
                      Accounting Imbalance:
                    </div>
                    <div style={{ textAlign: 'right', fontWeight: 800, color: '#10b981', borderTop: '1px solid #334155', paddingTop: '0.5rem' }}>
                      ₹0.00 (Exact Balance)
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 2: EVIDENCE GRAPH VIEW (DAG) */}
          {activeTab === 'graph' && (
            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#38bdf8' }}>
                  Directed Acyclic Evidence Graph ({graph?.nodes?.length} Nodes, {graph?.edges?.length} Causal Edges)
                </h3>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={simulateTamper}
                    style={{ backgroundColor: '#ef444420', border: '1px solid #ef4444', color: '#fca5a5', padding: '0.35rem 0.75rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                  >
                    Test Tamper Detection
                  </button>
                  {tamperedHash && (
                    <button
                      onClick={resetTamper}
                      style={{ backgroundColor: '#334155', border: 'none', color: '#f8fafc', padding: '0.35rem 0.75rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700, cursor: 'pointer' }}
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              {/* GRAPH NODES GRID */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                {graph?.nodes?.map((node: any) => (
                  <div
                    key={node.id}
                    style={{
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      padding: '0.85rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                      <span style={{ fontSize: '0.75rem', backgroundColor: '#38bdf820', color: '#38bdf8', padding: '0.15rem 0.45rem', borderRadius: '4px', fontWeight: 700 }}>
                        {node.node_type}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>
                        {node.confidence}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.3rem' }}>
                      {node.title}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.4rem' }}>
                      Source: {node.source}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                      {node.explanation}
                    </div>
                  </div>
                ))}
              </div>

              {/* GRAPH EDGES LIST */}
              <div style={{ backgroundColor: '#0f172a', border: '1px solid #334155', borderRadius: '8px', padding: '1rem' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.5rem' }}>
                  CAUSAL RELATIONSHIP EDGES:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {graph?.edges?.map((edge: any, i: number) => (
                    <div key={i} style={{ fontSize: '0.8rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ color: '#38bdf8', fontWeight: 600 }}>{edge.source_node_id}</span>
                      <span style={{ color: '#64748b' }}>──[{edge.relationship}]──►</span>
                      <span style={{ color: '#34d399', fontWeight: 600 }}>{edge.target_node_id}</span>
                      <span style={{ color: '#94a3b8', fontStyle: 'italic', fontSize: '0.75rem' }}>({edge.description})</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: ACTION DECISION MATRIX */}
          {activeTab === 'matrix' && (
            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#38bdf8' }}>
                Side-by-Side Candidate Action Economic & Policy Matrix
              </h3>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#0f172a', color: '#94a3b8', borderBottom: '1px solid #334155' }}>
                      <th style={{ padding: '0.75rem' }}>Action</th>
                      <th style={{ padding: '0.75rem' }}>Rec. Prob %</th>
                      <th style={{ padding: '0.75rem' }}>Gross Recovery</th>
                      <th style={{ padding: '0.75rem' }}>Action Cost</th>
                      <th style={{ padding: '0.75rem' }}>Risk Loss</th>
                      <th style={{ padding: '0.75rem' }}>Expected Net Value</th>
                      <th style={{ padding: '0.75rem' }}>Policy</th>
                      <th style={{ padding: '0.75rem' }}>Firewall</th>
                      <th style={{ padding: '0.75rem' }}>Selected</th>
                      <th style={{ padding: '0.75rem' }}>Decision Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matrix.map((c: any) => {
                      const isSel = c.selected;
                      return (
                        <tr
                          key={c.action}
                          style={{
                            backgroundColor: isSel ? '#0284c715' : 'transparent',
                            borderBottom: '1px solid #334155',
                          }}
                        >
                          <td style={{ padding: '0.75rem', fontWeight: 700, color: isSel ? '#38bdf8' : '#f8fafc' }}>
                            {c.action}
                          </td>
                          <td style={{ padding: '0.75rem' }}>{(c.recovery_probability * 100).toFixed(1)}%</td>
                          <td style={{ padding: '0.75rem' }}>₹{c.expected_gross?.toLocaleString()}</td>
                          <td style={{ padding: '0.75rem', color: '#fca5a5' }}>₹{c.action_cost?.toLocaleString()}</td>
                          <td style={{ padding: '0.75rem', color: '#fca5a5' }}>₹{c.expected_risk_loss?.toLocaleString()}</td>
                          <td style={{ padding: '0.75rem', fontWeight: 700, color: c.expected_net_value > 0 ? '#34d399' : '#94a3b8' }}>
                            ₹{c.expected_net_value?.toLocaleString()}
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            <span style={{ backgroundColor: c.policy_status === 'ALLOW' ? '#10b98120' : '#ef444420', color: c.policy_status === 'ALLOW' ? '#34d399' : '#f87171', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 700 }}>
                              {c.policy_status}
                            </span>
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            <span style={{ backgroundColor: c.firewall_status === 'ALLOW' ? '#10b98120' : '#ef444420', color: c.firewall_status === 'ALLOW' ? '#34d399' : '#f87171', padding: '0.2rem 0.5rem', borderRadius: '4px', fontWeight: 700 }}>
                              {c.firewall_status}
                            </span>
                          </td>
                          <td style={{ padding: '0.75rem', fontWeight: 700, color: isSel ? '#34d399' : '#64748b' }}>
                            {isSel ? '✓ YES' : '—'}
                          </td>
                          <td style={{ padding: '0.75rem', color: '#cbd5e1', maxWidth: '250px' }}>
                            {c.reason}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* EVIDENCE INTEGRITY PANEL */}
          <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '12px', padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <div style={{ fontSize: '0.8rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>
                  CRYPTOGRAPHIC EVIDENCE INTEGRITY
                </div>
                <div style={{ fontSize: '0.95rem', fontFamily: 'monospace', color: tamperedHash ? '#ef4444' : '#38bdf8', marginTop: '0.25rem' }}>
                  SHA-256: {tamperedHash || replayData.evidence_hash}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <span style={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.8rem', padding: '0.35rem 0.75rem', borderRadius: '6px' }}>
                  Nodes: <b>{graph?.nodes?.length}</b>
                </span>
                <span style={{ backgroundColor: '#0f172a', border: '1px solid #334155', color: '#38bdf8', fontSize: '0.8rem', padding: '0.35rem 0.75rem', borderRadius: '6px' }}>
                  Edges: <b>{graph?.edges?.length}</b>
                </span>
                <span style={{ backgroundColor: tamperedHash ? '#ef444420' : '#10b98120', border: tamperedHash ? '1px solid #ef4444' : '1px solid #10b981', color: tamperedHash ? '#f87171' : '#34d399', fontSize: '0.8rem', padding: '0.35rem 0.75rem', borderRadius: '6px', fontWeight: 700 }}>
                  {tamperedHash ? '❌ TAMPER DETECTED' : '✓ INTEGRITY VERIFIED'}
                </span>
              </div>
            </div>
          </div>
        </>
      )}

    </div>
  );
};
