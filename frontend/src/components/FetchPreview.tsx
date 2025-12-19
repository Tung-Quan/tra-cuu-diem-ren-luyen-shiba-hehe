// src/components/FetchPreview.tsx
import { useState } from "react";
import { fetchPreview } from "../lib/api";
import type { FetchPreviewResponse } from "../lib/api";

export default function FetchPreview() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState<FetchPreviewResponse | null>(null);
  const [err, setErr] = useState<string | undefined>();

  async function onFetch() {
    setErr(undefined);
    setResp(null);
    if (!url) return setErr("Nhập URL trước");
    setLoading(true);
    try {
      const r = await fetchPreview(url);
      setResp(r.data as FetchPreviewResponse);
    } catch (e: unknown) {
      const s = (e as any)?.response?.data?.error || String(e);
      setErr(s);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="flex gap-2">
        <input
          className="input"
          placeholder="Dán URL để xem preview…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <button className="btn" onClick={onFetch} disabled={loading}>
          {loading ? "Đang tải…" : "Fetch"}
        </button>
      </div>

      {err && <div className="text-red-600 mt-2">{err}</div>}

      {resp && (
        <div className="mt-3 space-y-3">
          <div className="text-sm text-gray-600">
            <div><span className="font-medium">Kind:</span> <code>{resp.kind}</code></div>
            {resp.file_id && <div><span className="font-medium">file_id:</span> <code>{resp.file_id}</code></div>}
            {resp.gid && <div><span className="font-medium">gid:</span> <code>{resp.gid}</code></div>}
            <div><span className="font-medium">fetched:</span> {resp.fetched ? "yes" : "no"}</div>
          </div>

          {!!resp.export_candidates?.length && (
            <div className="text-sm">
              <div className="font-medium">Export candidates</div>
              <ul className="list-disc ml-6">
                {resp.export_candidates.map((u, i) => <li key={i}><code className="break-all">{u}</code></li>)}
              </ul>
            </div>
          )}

          {resp.snippet && (
            <div>
              <div className="font-medium">Snippet</div>
              <pre className="mt-1 p-3 bg-slate-50 rounded overflow-auto text-xs whitespace-pre-wrap">
                {resp.snippet}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
