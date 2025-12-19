// src/pages/SheetsPage.tsx
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { DBStatsResponse } from "../lib/api";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

export default function SheetsPage() {
  const [data, setData] = useState<DBStatsResponse>();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    setLoading(true);
    api.get("/api/admin/db-stats")
      .then(r => setData(r.data))
      .catch(e => setErr(e?.response?.data?.error || String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="grid gap-4">
      <h2 className="text-xl font-semibold">Danh sách Sheets</h2>
      {loading && <Loading />}
      {err && <ErrorBanner message={err} />}

      {data && (
        <div className="card">
          <div className="text-sm grid sm:grid-cols-2 gap-y-2">
            <div>Số students: <strong>{data.students}</strong></div>
            <div>Số links: <strong>{data.links}</strong></div>
            <div>Số kết nối: <strong>{data.connections}</strong></div>
            <div>Students with links: <strong>{data.students_with_links}</strong></div>
          </div>

          {data.sheets && data.sheets.length > 0 && (
            <div className="mt-3">
              <div className="font-medium mb-1">Sheets sample</div>
              <ul className="list-disc ml-5 text-sm">
                {data.sheets.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
