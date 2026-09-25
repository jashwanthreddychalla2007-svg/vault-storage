import React, { useState, useEffect } from 'react';

/**
 * Vault — Interactive React Chaos UI & Node Topology Canvas Component
 * Built for v0.dev / Next.js integration.
 */
export default function VaultDashboard() {
  const [nodes, setNodes] = useState([
    { id: 1, name: "Storage-Node-A", status: "ONLINE", chunks: 8, usedKb: 512, corrupted: 0 },
    { id: 2, name: "Storage-Node-B", status: "ONLINE", chunks: 8, usedKb: 512, corrupted: 0 },
    { id: 3, name: "Storage-Node-C", status: "ONLINE", chunks: 7, usedKb: 448, corrupted: 0 },
    { id: 4, name: "Storage-Node-D", status: "ONLINE", chunks: 8, usedKb: 512, corrupted: 0 },
    { id: 5, name: "Storage-Node-E", status: "ONLINE", chunks: 6, usedKb: 384, corrupted: 0 },
  ]);

  const [logs, setLogs] = useState([
    { time: "00:55:10", type: "SYSTEM", text: "Raft Consensus Cluster Initialized. Leader: Node-A." },
    { time: "00:55:12", type: "QUORUM", text: "Object 'dataset.parquet' written (W=2, N=3). Vector Clock: (Node-A: 1)." }
  ]);

  const [activeTab, setActiveTab] = useState("topology");
  const [objects, setObjects] = useState([
    { id: "obj_9812a1", name: "system_config.json", policy: "RS (2+1)", merkle: "0xa4f8e912...", size: "12.4 KB" },
    { id: "obj_4410b2", name: "video_feed_01.mp4", policy: "3x Replication", merkle: "0x771c998f...", size: "45.2 MB" }
  ]);

  const addLog = (type, text) => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [{ time, type, text }, ...prev.slice(0, 30)]);
  };

  const killNode = (id) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, status: "FAILED" } : n));
    addLog("CHAOS", `⚡ KILLED STORAGE NODE ${id}. Missed gRPC Heartbeats.`);
  };

  const injectBitrot = (id) => {
    setNodes(prev => prev.map(n => n.id === id ? { ...n, corrupted: n.corrupted + 1, status: "BITROT" } : n));
    addLog("BITROT", `🧬 BIT-ROT INJECTED into Node ${id} chunk block 0x4a. SHA-256 Checksum Mismatch.`);
  };

  const triggerRepair = () => {
    setNodes(prev => prev.map(n => ({ ...n, status: "ONLINE", corrupted: 0 })));
    addLog("SELF_HEAL", "🔄 Background Merkle Scrub complete. Repaired corrupted chunks across surviving Quorums.");
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-gray-100 font-sans p-6">
      {/* Top Navigation */}
      <header class="flex items-center justify-between border-b border-gray-800 pb-4 mb-6">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-xl">
            🛡️
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">VAULT</h1>
            <p className="text-xs text-cyan-400 font-mono">FAULT-TOLERANT DISTRIBUTED STORAGE</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs rounded-full font-mono">
            Raft Leader: Active (Node 1)
          </span>
          <span className="px-3 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs rounded-full font-mono">
            Quorum: N=5, R=2, W=2
          </span>
        </div>
      </header>

      {/* Main 2-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Visual Canvas */}
        <div className="lg:col-span-8 space-y-6">
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 font-mono">
                📡 Live Cluster Nodes Topology & Health
              </h2>
              <button onClick={triggerRepair} className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20 px-3 py-1 rounded-lg text-xs font-mono transition">
                🔄 Trigger Auto Self-Healing
              </button>
            </div>

            {/* Nodes Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
              {nodes.map(n => (
                <div key={n.id} className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
                  n.status === 'FAILED' ? 'bg-red-950/30 border-red-500/40' :
                  n.status === 'BITROT' ? 'bg-amber-950/30 border-amber-500/40' :
                  'bg-gray-950 border-gray-800'
                }`}>
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold font-mono text-white">Node {n.id}</span>
                      <span className={`w-2 h-2 rounded-full ${
                        n.status === 'FAILED' ? 'bg-red-500' :
                        n.status === 'BITROT' ? 'bg-amber-500 animate-ping' :
                        'bg-emerald-500'
                      }`} />
                    </div>
                    <p className="text-[11px] text-gray-400 font-mono">Chunks: {n.chunks}</p>
                    <p className="text-[11px] text-gray-400 font-mono">Used: {n.usedKb} KB</p>
                  </div>

                  <div className="mt-3 pt-2 border-t border-gray-800/80 flex gap-1">
                    <button onClick={() => killNode(n.id)} className="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 text-[10px] py-1 rounded border border-red-500/20 font-mono">
                      Kill
                    </button>
                    <button onClick={() => injectBitrot(n.id)} className="flex-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-[10px] py-1 rounded border border-amber-500/20 font-mono">
                      Rot
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stored Objects Explorer */}
          <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 font-mono mb-4">
              📦 Objects Metadata & Vector Clocks
            </h2>
            <div className="overflow-x-auto">
              <table class="w-full text-left text-xs font-mono">
                <thead>
                  <tr class="border-b border-gray-800 text-gray-500">
                    <th class="pb-2">ID</th>
                    <th class="pb-2">Filename</th>
                    <th class="pb-2">Policy</th>
                    <th class="pb-2">Merkle Root</th>
                    <th class="pb-2 text-right">Size</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-800/60 text-gray-300">
                  {objects.map(o => (
                    <tr key={o.id} className="hover:bg-gray-800/30">
                      <td class="py-3 text-cyan-400 font-semibold">{o.id}</td>
                      <td class="py-3 text-white">{o.name}</td>
                      <td class="py-3"><span className="bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded">{o.policy}</span></td>
                      <td class="py-3 text-gray-500">{o.merkle}</td>
                      <td class="py-3 text-right text-gray-400">{o.size}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column: Terminal Audit Log */}
        <div className="lg:col-span-4 bg-gray-950 border border-gray-800 rounded-2xl p-5 flex flex-col">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 font-mono mb-3 pb-2 border-b border-gray-800 flex items-center justify-between">
            <span>📜 Real-Time Audit Console</span>
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          </h2>
          <div className="flex-1 overflow-y-auto space-y-2 text-[11px] font-mono max-h-[500px] pr-2">
            {logs.map((l, i) => (
              <div key={i} className="border-b border-gray-900 pb-1.5">
                <span className="text-gray-600">[{l.time}]</span>{' '}
                <span className={
                  l.type === 'CHAOS' ? 'text-red-400 font-bold' :
                  l.type === 'BITROT' ? 'text-amber-400 font-bold' :
                  l.type === 'SELF_HEAL' ? 'text-emerald-400 font-bold' : 'text-cyan-400'
                }>[{l.type}]</span>{' '}
                <span className="text-gray-300">{l.text}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
