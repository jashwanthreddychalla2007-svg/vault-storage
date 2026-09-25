import React from 'react';
import { Flame, RefreshCw, Zap, Bug, ShieldAlert } from 'lucide-react';

export default function ChaosPanel({ onKillRandom, onInjectBitrot, onRecoverCluster }) {
  return (
    <div className="bg-gray-900/60 border border-red-900/30 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-red-400 font-mono flex items-center gap-2">
          <Flame className="w-4 h-4 text-red-500 animate-pulse" />
          Chaos Control Studio
        </h2>
        <span className="text-[10px] font-mono bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-0.5 rounded">
          LIVE DEMO CHAOS
        </span>
      </div>

      <p className="text-xs text-gray-400 mb-4 leading-relaxed">
        Simulate hardware crashes, disk sector bit flips, and network failures live to demonstrate zero data loss.
      </p>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <button
          onClick={onKillRandom}
          className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 font-mono text-xs font-semibold p-3.5 rounded-xl flex flex-col items-center justify-center gap-1.5 transition active:scale-95"
        >
          <Zap className="w-5 h-5 text-red-400" />
          <span>Kill Random Node</span>
        </button>

        <button
          onClick={onInjectBitrot}
          className="bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/30 font-mono text-xs font-semibold p-3.5 rounded-xl flex flex-col items-center justify-center gap-1.5 transition active:scale-95"
        >
          <Bug className="w-5 h-5 text-amber-400" />
          <span>Inject Bitrot</span>
        </button>
      </div>

      <button
        onClick={onRecoverCluster}
        className="w-full bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono text-xs font-semibold p-3 rounded-xl flex items-center justify-center gap-2 transition active:scale-95"
      >
        <RefreshCw className="w-4 h-4" />
        <span>Recover All Cluster Nodes</span>
      </button>
    </div>
  );
}
