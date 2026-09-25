import React from 'react';
import { Server, Zap, AlertTriangle } from 'lucide-react';

export default function NodesGrid({ nodes, onKillNode, onInjectBitrot }) {
  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
          Storage Nodes Telemetry & Health
        </h2>
        <span className="text-[11px] text-slate-400 font-mono">Anti-Entropy: Enabled</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {nodes.map((n) => {
          const isFailed = n.status === 'FAILED';
          const isBitrot = n.corrupted_count > 0;

          return (
            <div key={n.node_id} className="bg-[#090D16] border border-slate-800 rounded p-3 flex flex-col justify-between space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-200 font-mono">{n.name}</span>
                {isFailed ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-rose-950 text-rose-400 border border-rose-800 font-mono font-bold">CRASHED</span>
                ) : isBitrot ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-mono font-bold">BITROT</span>
                ) : (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 font-mono font-bold">ONLINE</span>
                )}
              </div>

              <div className="text-[11px] text-slate-400 font-mono space-y-0.5">
                <p>Blocks: <span className="text-slate-200">{n.chunk_count}</span></p>
                <p>Used: <span className="text-slate-300">{(n.used_bytes / 1024).toFixed(1)} KB</span></p>
              </div>

              <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-1">
                <button
                  onClick={() => onKillNode(n.node_id)}
                  disabled={isFailed}
                  className="bg-rose-950/40 hover:bg-rose-900/60 disabled:opacity-30 text-rose-300 border border-rose-800/60 text-[10px] font-mono py-0.5 rounded transition"
                >
                  Kill
                </button>
                <button
                  onClick={() => onInjectBitrot(n.node_id)}
                  disabled={isFailed}
                  className="bg-amber-950/40 hover:bg-amber-900/60 disabled:opacity-30 text-amber-300 border border-amber-800/60 text-[10px] font-mono py-0.5 rounded transition"
                >
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
