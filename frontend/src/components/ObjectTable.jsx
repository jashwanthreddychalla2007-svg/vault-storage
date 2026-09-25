import React from 'react';
import { Download, Package } from 'lucide-react';

export default function ObjectTable({ objects, apiUrl }) {
  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-lg p-5">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
          Object Storage Inventory
        </h2>
        <span className="text-xs text-slate-400 font-mono">Objects: {objects.length}</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-slate-800 text-slate-400">
              <th className="pb-2">Object ID</th>
              <th className="pb-2">Key</th>
              <th className="pb-2">Policy</th>
              <th className="pb-2">Merkle Root</th>
              <th className="pb-2 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-300">
            {objects.length === 0 ? (
              <tr>
                <td colSpan="5" className="py-6 text-center text-slate-500">
                  No objects stored yet. Click "Upload Object" above to store your first payload.
                </td>
              </tr>
            ) : (
              objects.map((o) => (
                <tr key={o.object_id} className="hover:bg-[#090D16] transition">
                  <td className="py-2.5 text-indigo-400 font-medium">{o.object_id}</td>
                  <td className="py-2.5 text-slate-200">{o.filename}</td>
                  <td className="py-2.5">
                    <span className="bg-slate-800 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded text-[10px]">
                      {o.policy}
                    </span>
                  </td>
                  <td className="py-2.5 text-slate-500 font-mono">{o.merkle_root.substring(0, 12)}...</td>
                  <td className="py-2.5 text-right">
                    <a
                      href={`${apiUrl}/api/v1/objects/${o.object_id}/download`}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-2.5 py-1 rounded text-[10px] inline-flex items-center gap-1"
                    >
                      <Download className="w-3 h-3 text-indigo-400" />
                      <span>Download</span>
                    </a>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
