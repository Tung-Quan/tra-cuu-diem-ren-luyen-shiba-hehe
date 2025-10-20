// src/pages/MySQLSearchPage.tsx
import { useEffect, useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { mysqlSearch, mysqlCount, type MySQLActivity } from "../lib/api";
import SearchBar from "../components/SearchBar";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

type SheetSummaryItem = { sheet: string; count: number };

export default function MySQLSearchPage() {
  const [sp] = useSearchParams();
  const q = (sp.get("q") || "").trim();
  const [results, setResults] = useState<MySQLActivity[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();
  const [execTime, setExecTime] = useState<number>(0);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [limit, setLimit] = useState(50);

  // Load total count on mount
  useEffect(() => {
    mysqlCount()
      .then((r) => setTotalCount(r.data.count))
      .catch((e) => console.error("Failed to get count:", e));
  }, []);

  // Search when query changes
  useEffect(() => {
    setErr(undefined);
    setResults([]);
    if (!q || q.length < 2) return;

    setLoading(true);
    mysqlSearch(q, limit)
      .then((r) => {
        if (r.data.ok) {
          setResults(r.data.results);
          setExecTime(r.data.execution_time_ms);
        } else {
          setErr("Search failed");
        }
      })
      .catch((e) => {
        setErr(e?.response?.data?.error || String(e));
      })
      .finally(() => setLoading(false));
  }, [q, limit]);

  const sheetSummary: SheetSummaryItem[] = useMemo(() => {
    const map = new Map<string, number>();
    results.forEach((r) => map.set(r.sheet_name, (map.get(r.sheet_name) || 0) + 1));
    return Array.from(map.entries())
      .map(([sheet, count]) => ({ sheet, count }))
      .sort((a, b) => b.count - a.count);
  }, [results]);

  return (
    <div className="grid gap-4">
      <div className="card">
        <h1 className="text-2xl font-bold">🔍 MySQL Search - Tra Cứu Nhanh</h1>
        <p className="text-sm text-gray-600 mt-2">
          Tìm kiếm hoạt động theo đơn vị, chương trình. 
          Dữ liệu: {totalCount.toLocaleString()} activities trong MySQL.
        </p>
      </div>

      <SearchBar />

      {q && (
        <div className="text-sm text-gray-600">
          Từ khóa: <span className="font-medium">{q}</span>
          {execTime > 0 && <span className="ml-3">⚡ {execTime}ms</span>}
        </div>
      )}

      <div className="flex items-center gap-4 flex-wrap">
        <label className="text-sm flex items-center gap-2">
          <span>Giới hạn: {limit} kết quả</span>
          <input
            aria-label="limit"
            type="range"
            min={10}
            max={200}
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
          />
        </label>
      </div>

      {loading && <Loading />}
      {err && <ErrorBanner message={err} />}

      {!!sheetSummary.length && (
        <div className="card">
          <div className="font-medium mb-2">📊 Tổng hợp theo sheet</div>
          <div className="flex flex-wrap gap-2">
            {sheetSummary.map((item) => (
              <div key={item.sheet} className="px-3 py-1 bg-blue-100 rounded-full text-sm">
                {item.sheet}: <span className="font-medium">{item.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!!results.length && (
        <div className="grid gap-3">
          <div className="text-sm text-gray-600">
            Tìm thấy <span className="font-medium">{results.length}</span> kết quả
          </div>
          {results.map((r) => (
            <ActivityCard key={r.id} activity={r} />
          ))}
        </div>
      )}

      {q && !loading && results.length === 0 && !err && (
        <div className="card text-center text-gray-500">
          Không tìm thấy kết quả cho "{q}"
        </div>
      )}
    </div>
  );
}

// Activity Card Component
function ActivityCard({ activity }: { activity: MySQLActivity }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card hover:shadow-lg transition-shadow border-l-4 border-blue-500">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded">
              #{activity.mssv || activity.row_number}
            </span>
            <span className="text-xs text-gray-500">
              {activity.sheet_name} • Row {activity.row_number}
            </span>
            {activity.score && (
              <span className="text-xs text-gray-400">
                Score: {activity.score.toFixed(2)}
              </span>
            )}
          </div>

          {/* Main Content */}
          <div className="space-y-2">
            {activity.full_name && (
              <div>
                <span className="text-sm font-semibold text-gray-700">Đơn vị: </span>
                <span className="text-sm">{activity.full_name}</span>
              </div>
            )}

            {activity.unit && (
              <div>
                <span className="text-sm font-semibold text-gray-700">Mảng hoạt động: </span>
                <span className="text-sm">{activity.unit}</span>
              </div>
            )}

            {activity.program && (
              <div>
                <span className="text-sm font-semibold text-gray-700">Chương trình: </span>
                <div className={`text-sm mt-1 ${expanded ? '' : 'line-clamp-3'}`}>
                  {activity.program.split('\n').map((line, i) => (
                    <div key={i} className="ml-4">
                      {line.startsWith('-') || line.startsWith('•') ? line : `• ${line}`}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Expand Button */}
        {activity.program && activity.program.length > 200 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-blue-600 hover:text-blue-800 font-medium whitespace-nowrap"
          >
            {expanded ? '▲ Thu gọn' : '▼ Xem thêm'}
          </button>
        )}
      </div>
    </div>
  );
}
