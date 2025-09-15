// src/pages/SheetsPage.tsx
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { SheetsResponse } from "../lib/api";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

export default function SheetsPage() {
  const [data, setData] = useState<SheetsResponse>();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    setLoading(true);
    api.get("/sheets")
      .then(r => setData(r.data))
      .catch(e => setErr(e?.response?.data?.error || String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="grid gap-4">
      <h2 className="text-xl font-semibold">Danh sách Sheets</h2>
      {loading && <Loading />}
      {err && <ErrorBanner message={err} />}
      <div className="grid md:grid-cols-2 gap-3">
        {data?.sheets?.map((s, i) => (
          <div key={i} className="card">{s}</div>
        ))}
      </div>
      {!loading && !err && !data?.sheets?.length && (
        <div className="card">Không có dữ liệu.</div>
      )}
    </div>
  );
}
