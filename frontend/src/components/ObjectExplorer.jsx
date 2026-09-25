import React from 'react';
import { Package, Download, ShieldCheck, HardDrive } from 'lucide-react';

export default function ObjectExplorer({ objects, apiUrl }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-300 font-mono flex items-center gap-2">
          <Package className="w-4 h-4 text-cyan-400" />
          Stored Objects & Merkle Tree Index
        </h2>
        <span className="text-xs text-gray-500 font-mono">Count: {objects.length}</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead>
            <tr className="border-b border-gray-800 text-gray-500">
              <th className="pb-3">ID</th>
              <th className="pb-3">Filename</th>
              <th className="pb-3">Durability Policy</th>
              <th className="pb-3">Merkle Root</th>
              <th className="pb-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60 text-gray-300">
            {objects.length === 0 ? (
              <tr>
                <td colSpan="5" className="py-6 text-center text-gray-500">
                  No objects stored yet. Click "Upload Object" above to store your first payload.
                </td>
              </tr>
            ) : (
              objects.map((obj) => (
                <tr key={obj.object_id} className="hover:bg-gray-800/30 transition">
                  <td className="py-3.5 font-semibold text-cyan-400">{obj.object_id}</td>
                  <td className="py-3.5 text-white font-medium">{obj.filename}</td>
                  <td className="py-3.5">
                    <span className="bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2.5 py-1 rounded-lg text-[10px]">
                      {obj.policy}
                    </span>
                  </td>
                  <td className="py-3.5 text-gray-500 font-mono">
                    {obj.merkle_root.substring(0, 12)}...
                  </td>
                  <td className="py-3.5 text-right">
                    <a
                      href={`${apiUrl}/api/v1/objects/${obj.object_id}/download`}
                      className="bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 px-3 py-1.5 rounded-lg text-[11px] inline-flex items-center gap-1.5 transition"
                    >
                      <Download className="w-3 h-3 text-cyan-400" />
                      <span>Verify & Download</span>
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
