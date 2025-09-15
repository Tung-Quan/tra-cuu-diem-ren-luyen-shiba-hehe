// src/components/ResultCard.tsx
import { useState } from "react";
import type { Hit } from "../lib/api";

export default function ResultCard({ r }: { r: Hit }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="p-4 border rounded-2xl bg-white">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="text-lg font-semibold line-clamp-2">
            {r.snippet || "(không có trích đoạn)"}
          </div>
          <div className="text-sm text-gray-600">
            Sheet: <span className="font-medium">{r.sheet}</span> · Row: {r.row} · Score: {r.score}
          </div>
        </div>
        <button className="btn shrink-0" onClick={() => setOpen(!open)}>
          {open ? "Ẩn chi tiết" : "Xem chi tiết"}
        </button>
      </div>

      {open && (
        <div className="mt-3 space-y-3">
          {r.snippet_nodau && (
            <div className="text-xs text-gray-600">
              <div className="font-medium">Snippet (không dấu)</div>
              <pre className="mt-1 bg-slate-50 p-2 rounded whitespace-pre-wrap overflow-auto">
                {r.snippet_nodau}
              </pre>
            </div>
          )}
          <div className="text-xs">
            <div className="font-medium">Links ({r.links?.length || 0})</div>
            {r.links?.length ? (
              <ul className="list-disc ml-6 mt-1 space-y-1">
                {r.links.map((u, i) => (
                  <li key={i}><a className="text-blue-700 break-all" href={u} target="_blank" rel="noreferrer">{u}</a></li>
                ))}
              </ul>
            ) : <div className="text-gray-500">Không có link trong hàng này.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
