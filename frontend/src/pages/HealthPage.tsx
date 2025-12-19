import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "../lib/api";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

export default function HealthPage() {
  const [data, setData] = useState<HealthResponse>();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();

  useEffect(() => {
    setLoading(true);
    getHealth()
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
        <div className="card space-y-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold">Status:</span>
            <span className={data.status === "ok" ? "text-green-600" : "text-red-600"}>
              {data.status}
            </span>
          </div>
          
          <div className="text-sm text-gray-700">
            <div><strong>Database rows:</strong> {data.database_rows}</div>
            <div><strong>Sheets:</strong> {data.sheets.join(", ")}</div>
            <div><strong>Total links:</strong> {data.links.total}</div>
            <div><strong>Unique URLs:</strong> {data.links.unique_urls}</div>
          </div>

          <div className="text-sm border-t pt-3 space-y-1">
            <div className="font-medium">Services:</div>
            <div className="flex gap-4">
              <span className={data.mysql_available ? "text-green-600" : "text-gray-400"}>
                MySQL: {data.mysql_available ? "✓" : "✗"}
              </span>
              <span className={data.gspread_available ? "text-green-600" : "text-gray-400"}>
                GSpread: {data.gspread_available ? "✓" : "✗"}
              </span>
              <span className={data.google_api_available ? "text-green-600" : "text-gray-400"}>
                Google API: {data.google_api_available ? "✓" : "✗"}
              </span>
              <span className={data.deep_scan ? "text-green-600" : "text-gray-400"}>
                Deep Scan: {data.deep_scan ? "✓" : "✗"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
