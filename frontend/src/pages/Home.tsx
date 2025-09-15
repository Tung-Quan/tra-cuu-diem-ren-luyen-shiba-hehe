// src/pages/Home.tsx
import { useEffect, useState } from "react";
import { getHealth } from "../lib/api";

export default function Home() {
  const [info, setInfo] = useState<any>(null);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    getHealth()
      .then((r) => setInfo(r.data))
      .catch((e) => setErr(e?.response?.data?.error || String(e)));
  }, []);

  return (
    <div className="grid gap-4">
      <div className="card">
        <h1 className="text-2xl font-bold">Sheet Link Search</h1>
        <p className="text-gray-600">Giao diện tra cứu theo từ khóa & đường dẫn liên kết.</p>
      </div>

      {err && <div className="card text-red-700">{err}</div>}

      {info && (
        <div className="card">
          <div className="font-medium mb-2">Trạng thái backend</div>
          <ul className="text-sm grid sm:grid-cols-2 gap-y-1">
            <li>Rows: <strong>{info.rows}</strong></li>
            <li>Sheets: <strong>{info.sheets}</strong></li>
            <li>Unique links: <strong>{info.links}</strong></li>
            <li>OK: <strong>{String(info.ok)}</strong></li>
          </ul>

          <div className="text-sm text-gray-600 mt-3">Endpoints hữu ích:</div>
          <ul className="list-disc ml-5 text-sm">
            {["/search?q=...", "/sheets", "/links_index", "/debug/stats", "/debug/reindex?verbose=1&deep=1"].map((e) => (
              <li key={e}><code>{e}</code></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
