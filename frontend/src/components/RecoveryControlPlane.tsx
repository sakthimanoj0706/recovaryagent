import React, { useState, useEffect } from 'react';

const RecoveryControlPlane: React.FC = () => {
    const [metrics, setMetrics] = useState<any>(null);
    const [drift, setDrift] = useState<any>([]);
    const [challenger, setChallenger] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        try {
            // Need to pass token for auth ideally, but assuming mock auth for UI demo
            const headers = {
                'Authorization': 'Bearer ADMIN_MOCK_TOKEN'
            };
            
            const metRes = await fetch('/api/control/metrics', { headers });
            const driftRes = await fetch('/api/control/drift', { headers });
            const chalRes = await fetch('/api/control/challenger/latest', { headers });

            if (metRes.ok) setMetrics(await metRes.json());
            if (driftRes.ok) setDrift(await driftRes.json());
            if (chalRes.ok) {
                const c = await chalRes.json();
                setChallenger(c || null);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 10000);
        return () => clearInterval(interval);
    }, []);

    const evaluateChallenger = async () => {
        setLoading(true);
        await fetch('/api/control/challenger/evaluate?strat_id=chal_v2&version=v2.0.0', { 
            method: 'POST',
            headers: { 'Authorization': 'Bearer ADMIN_MOCK_TOKEN' }
        });
        fetchData();
    };

    const promoteChallenger = async () => {
        if (!challenger) return;
        setLoading(true);
        // Requires human approval
        await fetch(`/api/control/challenger/approve?strat_id=${challenger.id}`, { method: 'POST', headers: { 'Authorization': 'Bearer ADMIN_MOCK_TOKEN' }});
        await fetch(`/api/control/challenger/promote?strat_id=${challenger.id}`, { method: 'POST', headers: { 'Authorization': 'Bearer ADMIN_MOCK_TOKEN' }});
        fetchData();
    };

    if (loading && !metrics) return <div>Loading Control Plane...</div>;

    return (
        <div className="bg-white shadow rounded-lg p-6 my-4 border border-indigo-100">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 border-b pb-2 flex items-center">
                <span className="text-indigo-600 mr-2">🎛️</span> Operator Control Plane
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                {/* Economics */}
                <div className="bg-gray-50 p-4 rounded border">
                    <h3 className="font-bold mb-2">Expected vs Actual Economics</h3>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <div className="text-sm text-gray-500">Expected Net Value</div>
                            <div className="text-lg font-mono">₹{metrics?.expected_net_value?.toFixed(2) || '0.00'}</div>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500">Actual Net Value</div>
                            <div className="text-lg font-mono font-bold text-green-700">₹{metrics?.actual_net_value?.toFixed(2) || '0.00'}</div>
                        </div>
                        <div>
                            <div className="text-sm text-gray-500">Expected Recovery Rate</div>
                            <div className="text-lg font-mono">{((metrics?.recovery_rate || 0) * 100).toFixed(1)}%</div>
                        </div>
                    </div>
                </div>

                {/* Drift */}
                <div className="bg-gray-50 p-4 rounded border">
                    <h3 className="font-bold mb-2">Policy Drift Detection</h3>
                    {drift && drift.length > 0 ? drift.map((d: any, idx: number) => (
                        <div key={idx} className="flex justify-between items-center mb-2">
                            <span className="text-sm text-gray-700 font-mono">{d.metric}</span>
                            <span className={`px-2 py-1 text-xs font-bold rounded ${d.status === 'STABLE' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                                {d.status}
                            </span>
                        </div>
                    )) : <div className="text-sm text-gray-500">No drift data.</div>}
                </div>
            </div>

            {/* Challenger */}
            <div className="bg-indigo-50 p-4 rounded border border-indigo-200">
                <h3 className="font-bold mb-2 flex items-center justify-between">
                    <span>Champion vs Challenger</span>
                    <button 
                        onClick={evaluateChallenger}
                        disabled={loading}
                        className="text-xs bg-indigo-600 text-white px-3 py-1 rounded hover:bg-indigo-700"
                    >
                        Run Offline Evaluation
                    </button>
                </h3>
                
                {challenger ? (
                    <div>
                        <div className="flex justify-between items-center mb-4 border-b border-indigo-100 pb-2">
                            <div className="text-sm">
                                <strong>Status:</strong> <span className="font-mono bg-white px-1 rounded border">{challenger.status}</span>
                            </div>
                            <div className="text-sm">
                                <strong>Proof Hash:</strong> <span className="font-mono text-xs">{challenger.proof_hash?.substring(0, 12)}...</span>
                            </div>
                        </div>
                        
                        {challenger.evaluation_results && challenger.evaluation_results.CHALLENGER ? (
                            <div className="grid grid-cols-2 gap-4 mb-4">
                                <div className="bg-white p-2 rounded border">
                                    <div className="text-xs text-gray-500">Champion Net Value</div>
                                    <div className="font-mono">₹{challenger.evaluation_results.DETERMINISTIC.net_value.toFixed(2)}</div>
                                </div>
                                <div className="bg-white p-2 rounded border border-indigo-300">
                                    <div className="text-xs text-indigo-700 font-bold">Challenger Net Value</div>
                                    <div className="font-mono">₹{challenger.evaluation_results.CHALLENGER.net_value.toFixed(2)}</div>
                                </div>
                                <div className="bg-white p-2 rounded border">
                                    <div className="text-xs text-gray-500">Safety Violations</div>
                                    <div className="font-mono text-red-600">{challenger.evaluation_results.CHALLENGER.viol}</div>
                                </div>
                            </div>
                        ) : null}

                        {challenger.status === 'APPROVAL_REQUIRED' && (
                            <button 
                                onClick={promoteChallenger}
                                className="w-full bg-green-600 text-white font-bold py-2 rounded hover:bg-green-700 shadow"
                            >
                                APPROVE AND PROMOTE TO CHAMPION (Admin Only)
                            </button>
                        )}
                        {challenger.status === 'REJECTED' && (
                            <div className="text-sm text-red-600 font-bold bg-red-50 p-2 rounded text-center">
                                Challenger Rejected due to safety violation bounds.
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="text-sm text-gray-500">No active challenger. Run evaluation.</div>
                )}
            </div>
            
            <div className="mt-4 text-xs text-gray-400">
                All learned intelligence strictly observes Deterministic Financial State limitations. No strategy auto-promotes. Live financial ledger state writes are completely walled off.
            </div>
        </div>
    );
};

export default RecoveryControlPlane;
