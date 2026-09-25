import React from 'react';
import { Terminal } from 'lucide-react';

export default function AuditTerminal({ logs }) {
  return (
    <div className="bg-gray-950 border border-gray-800 rounded-2xl p-5 flex-1 flex flex-col shadow-2xl">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-800/80">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400 font-mono flex items-center gap-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          Real-Time Audit Console
        </h3>
        <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 text-[11px] font-mono pr-2 max-h-[350px]">
        {logs.length === 0 ? (
          <p className="text-gray-600 italic">Listening for cluster telemetry events...</p>
        ) : (
          logs.map((log, idx) => {
            let catColor = "text-cyan-400 font-semibold";
            if (log.category === "CHAOS" || log.category === "ERROR") catColor = "text-red-400 font-bold";
            if (log.category === "BITROT_ALERT") catColor = "text-amber-400 font-bold";
            if (log.category === "SELF_HEAL") catColor = "text-emerald-400 font-bold";

            return (
              <div key={idx} className="border-b border-gray-900/80 pb-1.5 leading-relaxed">
                <span className="text-gray-600">[{log.timestamp}]</span>{' '}
                <span className={catColor}>[{log.category}]</span>{' '}
                <span className="text-gray-300">{log.message}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
