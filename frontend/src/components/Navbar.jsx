import React from 'react';
import { Server, HardDrive, Plus, Activity } from 'lucide-react';

export default function Navbar({ onlineCount, onOpenUpload }) {
  return (
    <header className="border-b border-slate-800 bg-[#0F172A]/90 backdrop-blur px-6 py-3.5 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center space-x-3.5">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold text-sm shadow-sm font-sans">
          V
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm font-semibold text-white tracking-tight font-sans">Vault Storage Console</h1>
            <span className="text-[10px] bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 rounded font-mono">
              v1.2.0-prod
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-mono">Region: us-east-1 (Quorum N=5, R=2, W=2)</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 bg-[#090D16] px-3 py-1.5 rounded-md border border-slate-800 text-xs font-mono">
          <span className={`w-2 h-2 rounded-full ${onlineCount === 5 ? 'bg-emerald-500' : 'bg-rose-500 animate-pulse'}`} />
          <span className="text-slate-200">{onlineCount}/5 Nodes Healthy</span>
        </div>

        <button
          onClick={onOpenUpload}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-3.5 py-1.5 rounded-md text-xs font-sans tracking-wide transition shadow-sm flex items-center gap-1.5 active:scale-95"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Upload Object</span>
        </button>
      </div>
    </header>
  );
}
