import React, { useState, useEffect } from 'react';

const IntelligentRecoveryPanel: React.FC = () => {
    const [latest, setLatest] = useState<any>(null);

    useEffect(() => {
        fetch('/api/intelligence/latest')
            .then(res => res.json())
            .then(data => setLatest(data))
            .catch(err => console.error(err));
    }, []);

    return (
        <div className="bg-white shadow rounded-lg p-6 my-4 border border-blue-100">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 border-b pb-2 flex items-center">
                <span className="text-blue-600 mr-2">🤖</span> Intelligent Recovery Engine
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-md">
                    <div className="text-sm text-gray-500 mb-1">Status</div>
                    <div className="text-lg font-bold text-blue-700">
                        {latest ? (latest.status === 'active' ? 'Active' : 'Offline') : 'Loading...'}
                    </div>
                </div>
                
                <div className="bg-green-50 p-4 rounded-md">
                    <div className="text-sm text-gray-500 mb-1">Decisions Made</div>
                    <div className="text-lg font-bold text-green-700">
                        {latest ? latest.decisions_made.toLocaleString() : '0'}
                    </div>
                </div>

                <div className="bg-indigo-50 p-4 rounded-md">
                    <div className="text-sm text-gray-500 mb-1">Engine Mode</div>
                    <div className="text-lg font-bold text-indigo-700">
                        {latest && latest.models_loaded ? 'Advisory LLM + Deterministic Firewall' : 'Deterministic Only'}
                    </div>
                </div>
            </div>

            <div className="bg-gray-50 p-4 rounded-md text-sm text-gray-600">
                <p className="mb-2"><strong>Deterministic Supremacy Active:</strong> The LLM is restricted to an advisory role. All generated candidates are deterministically ranked by maximum Expected Net Value.</p>
                <p>If the LLM recommends an ineligible action, or an action with a negative economic delta compared to the deterministic baseline, the system automatically overrides it to prevent financial loss.</p>
            </div>
        </div>
    );
};

export default IntelligentRecoveryPanel;
