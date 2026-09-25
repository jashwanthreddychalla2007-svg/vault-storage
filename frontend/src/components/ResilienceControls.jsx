import React from 'react';
import { ShieldAlert, Bug, RefreshCw } from 'lucide-react';

export default function ResilienceControls({ onKillRandom, onInjectBitrot, onRecoverCluster }) {
  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-5">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono mb-2">
        Resilience Simulation Controls
      </h2>
      <p className="text-xs text-slate-400 mb-4">Execute controlled node failures and disk bitrot corruption to test quorum resilience.</p>

      <div className="grid grid-cols-2 gap-2.5">
        <button
          onClick={onKillRandom}
          className="bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800/80 font-mono text-xs font-medium py-2.5 px-3 rounded transition flex items-center justify-center gap-1.5"
        >
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <span>Simulate Node Death</span>
        </button>

        <button
          onClick={onInjectBitrot}
          className="bg-amber-950/40 hover:bg-amber-900/60 text-amber-300 border border-amber-800/80 font-mono text-xs font-medium py-2.5 px-3 rounded transition flex items-center justify-center gap-1.5"
        >
          <Bug className="w-4 h-4 text-amber-400" />
          <span>Inject Disk Bitrot</span>
        </button>
      </div>

      <button
        onClick={onRecoverCluster}
        className="w-full mt-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono text-xs font-medium py-2 rounded transition flex items-center justify-center gap-1.5"
      >
        <RefreshCw className="w-3.5 h-3.5" />
        <span>Reset Cluster State</span>
      </button>
    </div>
  );
}
