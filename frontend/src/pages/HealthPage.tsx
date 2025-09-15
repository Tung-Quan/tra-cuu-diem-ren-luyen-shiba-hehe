import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { SheetsResponse } from "../lib/api";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

export default function HealthPage() {
  const [data, setData] = useState<HealthResponse>();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    setLoading(true);
    api.get("/health")
      .then(r => setData(r.data))
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="grid gap-4">
      <h2 className="text-xl font-semibold">Trạng thái Backend</h2>
      {loading && <Loading />}
      {err && <ErrorBanner message={err} />}
      {data && (
        <div className="card">
          <div className="font-medium">Status: {data.status}</div>
          {typeof data.total_entries === "number" && (
            <div className="text-sm text-gray-600">
              Tổng entries: {data.total_entries}
            </div>
          )}
          {data.message && <div className="text-sm">{data.message}</div>}
        </div>
      )}
    </div>
  );
}
