import React from 'react';
import { Database, ShieldCheck, Activity, Clock } from 'lucide-react';

export default function MetricsHeader({ objectCount, totalBytes }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-xs font-medium">Total Cluster Storage</span>
          <Database className="w-4 h-4 text-slate-500" />
        </div>
        <p className="text-xl font-semibold text-white font-mono">
          {(totalBytes / 1024).toFixed(1)} KB <span class="text-xs font-normal text-slate-400">/ 50.0 GB</span>
        </p>
      </div>

      <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-xs font-medium">Active Storage Policy</span>
          <ShieldCheck className="w-4 h-4 text-indigo-400" />
        </div>
        <p className="text-xl font-semibold text-indigo-400 font-mono">Reed-Solomon (2+1)</p>
      </div>

      <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-xs font-medium">Anti-Entropy Scrubber</span>
          <Activity className="w-4 h-4 text-emerald-400" />
        </div>
        <p className="text-xl font-semibold text-emerald-400 font-mono">Active (5s Loop)</p>
      </div>

      <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between text-slate-400 mb-1">
          <span className="text-xs font-medium">Mean Recovery Latency</span>
          <Clock className="w-4 h-4 text-slate-500" />
        </div>
        <p className="text-xl font-semibold text-slate-200 font-mono">&lt; 140 ms</p>
      </div>
    </div>
  );
}
