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

      {/* Quick Links */}
      <div className="grid sm:grid-cols-2 gap-4">
        <a href="/search" className="card hover:shadow-lg transition-shadow bg-blue-50 border-l-4 border-blue-500">
          <div className="text-lg font-semibold mb-1">🔍 Tìm Kiếm Google Sheets</div>
          <p className="text-sm text-gray-600">Tìm trong dữ liệu Google Sheets với link fetching</p>
        </a>
        
        <a href="/mysql" className="card hover:shadow-lg transition-shadow bg-green-50 border-l-4 border-green-500">
          <div className="text-lg font-semibold mb-1">⚡ MySQL Search</div>
          <p className="text-sm text-gray-600">Tìm kiếm nhanh trong database (recommended)</p>
        </a>
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
            {["/search?q=...", "/mysql/ctv/search?q=...", "/sheets", "/links_index", "/debug/stats"].map((e) => (
              <li key={e}><code>{e}</code></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
