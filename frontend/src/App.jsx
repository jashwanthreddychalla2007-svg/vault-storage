import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import MetricsHeader from './components/MetricsHeader';
import NodesGrid from './components/NodesGrid';
import ObjectTable from './components/ObjectTable';
import ResilienceControls from './components/ResilienceControls';
import EventTerminal from './components/EventTerminal';

const API_URL = "http://localhost:8000";

export default function App() {
  const [nodes, setNodes] = useState([]);
  const [objects, setObjects] = useState([]);
  const [logs, setLogs] = useState([]);
  const [totalBytes, setTotalBytes] = useState(0);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Upload Form states
  const [file, setFile] = useState(null);
  const [policy, setPolicy] = useState("REED_SOLOMON_2_1");

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/cluster/status`);
      const data = await res.json();
      setNodes(data.nodes || []);
      setLogs(data.event_logs || []);
      setTotalBytes(data.total_used_bytes || 0);
    } catch (err) {
      console.error("Backend offline", err);
    }
  };

  const fetchObjects = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/objects`);
      const data = await res.json();
      setObjects(data || []);
    } catch (err) {
      console.error("Objects error", err);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchObjects();
    const interval = setInterval(() => {
      fetchStatus();
      fetchObjects();
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  const handleKillNode = async (nodeId) => {
    const body = new FormData();
    body.append('node_id', nodeId);
    await fetch(`${API_URL}/api/v1/chaos/kill-node`, { method: 'POST', body });
    fetchStatus();
  };

  const handleInjectBitrot = async (nodeId) => {
    const body = new FormData();
    body.append('node_id', nodeId || Math.floor(Math.random() * 5) + 1);
    await fetch(`${API_URL}/api/v1/chaos/bitrot`, { method: 'POST', body });
    fetchStatus();
  };

  const handleRecoverCluster = async () => {
    await fetch(`${API_URL}/api/v1/chaos/recover`, { method: 'POST' });
    fetchStatus();
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('policy', policy);

    await fetch(`${API_URL}/api/v1/objects/upload`, { method: 'POST', body: formData });
    setIsUploadOpen(false);
    setFile(null);
    fetchStatus();
    fetchObjects();
  };

  const onlineCount = nodes.filter(n => n.status === 'ONLINE').length;

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 font-sans flex flex-col antialiased">
      <Navbar onlineCount={onlineCount} onOpenUpload={() => setIsUploadOpen(true)} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Metrics Overview Header */}
        <MetricsHeader objectCount={objects.length} totalBytes={totalBytes} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <NodesGrid nodes={nodes} onKillNode={handleKillNode} onInjectBitrot={handleInjectBitrot} />
            <ObjectTable objects={objects} apiUrl={API_URL} />
          </div>

          {/* Right Column (5 cols) */}
          <div className="lg:col-span-5 space-y-6 flex flex-col">
            <ResilienceControls
              onKillRandom={() => handleKillNode(Math.floor(Math.random() * 5) + 1)}
              onInjectBitrot={() => handleInjectBitrot()}
              onRecoverCluster={handleRecoverCluster}
            />
            <EventTerminal logs={logs} />
          </div>
        </div>
      </main>

      {/* Upload Modal */}
      {isUploadOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm hidden flex items-center justify-center p-4 z-50">
          <div className="bg-[#0F172A] border border-slate-800 rounded-lg max-w-md w-full p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white font-sans">Upload New Storage Payload</h3>
            <form onSubmit={handleUploadSubmit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Select Local File</label>
                <input
                  type="file"
                  required
                  onChange={(e) => setFile(e.target.files[0])}
                  className="w-full bg-[#090D16] border border-slate-800 rounded p-2 text-xs text-slate-300 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-slate-400 mb-1">Select Storage Policy</label>
                <select
                  value={policy}
                  onChange={(e) => setPolicy(e.target.value)}
                  className="w-full bg-[#090D16] border border-slate-800 rounded p-2 text-xs text-slate-300 font-mono"
                >
                  <option value="REED_SOLOMON_2_1">Reed-Solomon 2+1 (High Efficiency)</option>
                  <option value="REPLICATION_3X">3x Replication (Full Redundancy)</option>
                </select>
              </div>
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsUploadOpen(false)}
                  className="px-3 py-1.5 text-xs text-slate-400 hover:text-white font-sans"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3 py-1.5 rounded text-xs font-sans"
                >
                  Confirm Upload
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
