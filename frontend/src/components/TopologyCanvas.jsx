import React from 'react';
import { Server, AlertTriangle, Zap, ShieldCheck } from 'lucide-react';

export default function TopologyCanvas({ nodes, onKillNode, onInjectBitrot }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 relative overflow-hidden shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-300 font-mono flex items-center gap-2">
            <Server className="w-4 h-4 text-cyan-400" />
            Active Storage Nodes Topology (N=5)
          </h2>
          <p className="text-xs text-gray-500 font-mono mt-0.5">Real-time health telemetry & chunk distribution</p>
        </div>
        <span className="text-xs text-cyan-400 font-mono bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 rounded-lg">
          Sync: 1.0s
        </span>
      </div>

      {/* Nodes Array Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
        {nodes.map((node) => {
          const isFailed = node.status === 'FAILED';
          const isBitrot = node.corrupted_count > 0;

          return (
            <div
              key={node.node_id}
              className={`p-4 rounded-xl border flex flex-col justify-between transition-all duration-300 relative ${
                isFailed
                  ? 'bg-red-950/20 border-red-500/40 shadow-lg shadow-red-500/10'
                  : isBitrot
                  ? 'bg-amber-950/20 border-amber-500/40 shadow-lg shadow-amber-500/10'
                  : 'bg-gray-950 border-gray-800 hover:border-gray-700'
              }`}
            >
              {/* Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
                    <Server className={`w-3.5 h-3.5 ${isFailed ? 'text-red-400' : isBitrot ? 'text-amber-400' : 'text-cyan-400'}`} />
                    Node {node.node_id}
                  </span>
                  <span
                    className={`text-[9px] px-2 py-0.5 rounded-full font-mono font-bold ${
                      isFailed
                        ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                        : isBitrot
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {isFailed ? 'CRASHED' : isBitrot ? 'BITROT' : 'ONLINE'}
                  </span>
                </div>

                <div className="space-y-1 mt-3 text-[11px] font-mono text-gray-400">
                  <div className="flex justify-between">
                    <span>Chunks:</span>
                    <strong className="text-gray-200">{node.chunk_count}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Used:</span>
                    <strong className="text-gray-200">{(node.used_bytes / 1024).toFixed(1)} KB</strong>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-4 pt-3 border-t border-gray-800/80 grid grid-cols-2 gap-1.5">
                <button
                  onClick={() => onKillNode(node.node_id)}
                  disabled={isFailed}
                  className="bg-red-500/10 hover:bg-red-500/20 disabled:opacity-30 text-red-400 border border-red-500/20 text-[10px] font-mono py-1 rounded-lg transition flex items-center justify-center gap-1"
                >
                  <Zap className="w-3 h-3" />
                  Kill
                </button>
                <button
                  onClick={() => onInjectBitrot(node.node_id)}
                  disabled={isFailed}
                  className="bg-amber-500/10 hover:bg-amber-500/20 disabled:opacity-30 text-amber-400 border border-amber-500/20 text-[10px] font-mono py-1 rounded-lg transition flex items-center justify-center gap-1"
                >
                  <AlertTriangle className="w-3 h-3" />
                  Bitrot
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
