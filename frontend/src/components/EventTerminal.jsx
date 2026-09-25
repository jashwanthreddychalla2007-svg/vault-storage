import React from 'react';
import { Terminal } from 'lucide-react';

export default function EventTerminal({ logs }) {
  return (
    <div className="bg-[#090D16] border border-slate-800 rounded-lg p-4 flex-1 flex flex-col shadow-inner">
      <div className="flex items-center justify-between mb-2.5 border-b border-slate-800 pb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          System Event Stream
        </h3>
        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 text-[11px] font-mono max-h-80 pr-1">
        {logs.length === 0 ? (
          <p className="text-slate-600 italic">Listening for cluster telemetry events...</p>
        ) : (
          logs.map((l, i) => (
            <div key={i} className="border-b border-slate-900 pb-1">
              <span className="text-slate-500">[{l.timestamp}]</span>{' '}
              <span className="text-indigo-400">[{l.category}]</span>{' '}
              <span className="text-slate-300">{l.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
