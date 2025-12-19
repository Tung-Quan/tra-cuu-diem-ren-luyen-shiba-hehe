// src/pages/MySQLSearchPage.tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { mysqlSearch, type MySQLStudent } from "../lib/api";
import SearchBar from "../components/SearchBar";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

export default function MySQLSearchPage() {
  const [sp] = useSearchParams();
  const q = (sp.get("q") || "").trim();
  const [results, setResults] = useState<MySQLStudent[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();
  const [execTime, setExecTime] = useState<number>(0);
  const [limit, setLimit] = useState(50);

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
  return (
    <div className="grid gap-4">
      <div className="card">
        <h1 className="text-2xl font-bold"> MySQL Search - Tra Cứu Sinh Viên</h1>
        <p className="text-sm text-gray-600 mt-2">
          Tìm kiếm sinh viên theo tên hoặc MSSV. Dữ liệu từ MySQL database.
        </p>
      </div>

      <SearchBar />

      {q && (
        <div className="text-sm text-gray-600">
          Từ khóa: <span className="font-medium">{q}</span>
          {execTime > 0 && <span className="ml-3">{execTime.toFixed(2)}ms</span>}
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

      {q && !loading && results.length === 0 && !err && (
        <div className="card text-center text-gray-500">Không tìm thấy kết quả cho "{q}"</div>
      )}

      {results.length > 0 && (
        <div className="grid gap-3">
          <div className="grid gap-3">
            {results.map((student) => (
              <StudentCard key={student.student_id} student={student} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Student Card Component
function StudentCard({ student }: { student: MySQLStudent }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card hover:shadow-lg transition-shadow border-l-4 border-blue-500">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs rounded font-mono">
              {student.mssv}
            </span>
          </div>

          {/* Main Content */}
          <div className="space-y-2">
            <div>
              <span className="text-base font-semibold text-gray-900">{student.full_name}</span>
            </div>

            {student.links && student.links.length > 0 && (
              <div>
                <div className="text-sm font-semibold text-gray-700 mb-1">
                  Tham gia {student.links.length} chương trình:
                </div>
                <div className={`space-y-2 ${expanded ? '' : 'max-h-32 overflow-hidden'}`}>
                  {(() => {
                    // Sort links by gid (group identifier) then by sheet_name/row
                    const links = [...student.links].sort((a, b) => {
                      const ga = (a.gid || a.sheet_name || '').toString();
                      const gb = (b.gid || b.sheet_name || '').toString();
                      if (ga === gb) return (a.row_number || 0) - (b.row_number || 0);
                      return ga.localeCompare(gb, undefined, { sensitivity: 'base' });
                    });

                    // Group by gid (or sheet_name fallback)
                    const groups: Record<string, typeof links> = {};
                    for (const l of links) {
                      const key = (l.gid || l.sheet_name || 'Unknown').toString();
                      groups[key] = groups[key] || [];
                      groups[key].push(l);
                    }

                    return Object.keys(groups).map((gid) => (
                      <div key={gid} className="mb-2">
                        <div className="text-xs text-gray-500 font-medium mb-1">{gid}</div>
                        <div className="space-y-2">
                          {groups[gid].map((link) => {
                            const titleLabel = link.title && link.title.length > 120
                              ? `${link.title.slice(0, 120)}…`
                              : link.title || link.sheet_name || 'Unknown Sheet';

                            return (
                              <div key={link.link_id} className="ml-4 text-sm border-l-2 pl-3 border-gray-200">
                                <div className="font-medium text-gray-800">
                                  {link.url ? (
                                    <a
                                      href={link.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      title={link.title || ''}
                                      className="text-blue-700 hover:text-blue-900"
                                    >
                                      {titleLabel}
                                    </a>
                                  ) : (
                                    <span title={link.title || ''}>{titleLabel}</span>
                                  )}

                                  {link.row_number && (
                                    <span className="text-gray-400 ml-2 text-xs">Row {link.row_number}</span>
                                  )}

                                  {/* Show sheet_name separately from title */}
                                  {link.sheet_name && (
                                    <div className="text-xs text-gray-500 mt-1">{link.sheet_name}</div>
                                  )}
                                </div>

                                {link.snippet && (
                                  <div className="text-gray-600 text-xs mt-1">{link.snippet}</div>
                                )}

                                {link.url && (
                                  <div className="mt-1">
                                    <a
                                      href={link.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:text-blue-800 text-xs inline-flex items-center gap-1"
                                    >
                                      Xem chi tiết →
                                    </a>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ));
                  })()}
                  
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Expand Button */}
        {student.links && student.links.length > 2 && (
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
