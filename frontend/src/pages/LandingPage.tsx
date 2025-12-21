// src/pages/LandingPage.tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { mysqlSearch, getHealth, type MySQLStudent, type HealthResponse } from "../lib/api";
import SearchBar from "../components/SearchBar";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";

export default function LandingPage() {
  const [sp] = useSearchParams();
  const q = (sp.get("q") || "").trim();
  const [results, setResults] = useState<MySQLStudent[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();
  const [execTime, setExecTime] = useState<number>(0);
  const [limit, setLimit] = useState(50);
  const [healthData, setHealthData] = useState<HealthResponse>();
  const [showHealth, setShowHealth] = useState(false);

  // Load health data on mount
  useEffect(() => {
    getHealth()
      .then(r => setHealthData(r.data))
      .catch(() => {});
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100">
      {/* Hero Section with Health Status */}
      <div className="relative overflow-hidden bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDE2YzAtNC40MTggMy41ODItOCA4LThzOCAzLjU4MiA4IDgtMy41ODIgOC04IDgtOC0zLjU4Mi04LTh6bS04IDBjMC00LjQxOCAzLjU4Mi04IDgtOHM4IDMuNTgyIDggOC0zLjU4MiA4LTggOC04LTMuNTgyLTgtOHptLTE2IDBjMC00LjQxOCAzLjU4Mi04IDgtOHM4IDMuNTgyIDggOC0zLjU4MiA4LTggOC04LTMuNTgyLTgtOHoiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-20"></div>
        
        <div className="relative max-w-7xl mx-auto px-6 py-16">
          {/* Title Section */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 mb-4 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              <span className="text-sm font-medium">System Online</span>
            </div>
            
            <h1 className="text-5xl md:text-6xl font-bold mb-4 tracking-tight">
              Tra Cứu Sinh Viên
            </h1>
            <p className="text-xl text-slate-300 max-w-2xl mx-auto">
              Tìm kiếm thông tin sinh viên nhanh chóng và chính xác thông qua hệ thống MySQL
            </p>
          </div>

          {/* Health Status Cards */}
          {healthData && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{healthData.database_rows.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Database Records</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{healthData.links.total.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Total Links</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{healthData.links.unique_urls.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Unique URLs</div>
              </div>
              
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{healthData.sheets.length}</div>
                <div className="text-sm text-slate-300">Sheets Indexed</div>
              </div>
            </div>
          )}

          {/* Services Status - Expandable */}
          <div className="flex justify-center">
            <button
              onClick={() => setShowHealth(!showHealth)}
              className="group inline-flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-full border border-white/20 transition-all duration-300"
            >
              <span className="text-sm font-medium">System Services</span>
              <svg 
                className={`w-4 h-4 transition-transform duration-300 ${showHealth ? 'rotate-180' : ''}`}
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          {showHealth && healthData && (
            <div className="mt-6 bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20 animate-in fade-in slide-in-from-top-4 duration-500">
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Service Status
                  </h3>
                  <div className="space-y-3">
                    <StatusItem label="MySQL Database" active={healthData.mysql_available} />
                    <StatusItem label="Google Sheets API" active={healthData.gspread_available} />
                    <StatusItem label="Google Drive API" active={healthData.google_api_available} />
                    <StatusItem label="Deep Scan Mode" active={healthData.deep_scan} />
                  </div>
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Indexed Sheets
                  </h3>
                  <div className="max-h-32 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                    {healthData.sheets.map((sheet, idx) => (
                      <div key={idx} className="text-sm bg-white/5 rounded-lg px-3 py-2 border border-white/10">
                        {sheet}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Search Section */}
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="bg-white rounded-3xl shadow-2xl shadow-slate-200/50 p-8 border border-slate-100">
          <SearchBar />

          {q && (
            <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
              <div>
                Kết quả cho: <span className="font-semibold text-gray-900">"{q}"</span>
                {execTime > 0 && <span className="ml-3 text-gray-400">({execTime.toFixed(2)}ms)</span>}
              </div>
              
              <label className="flex items-center gap-3">
                <span className="text-gray-700">Giới hạn:</span>
                <select
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  className="px-3 py-1 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                </select>
              </label>
            </div>
          )}

          {loading && (
            <div className="mt-8">
              <Loading />
            </div>
          )}
          
          {err && (
            <div className="mt-8">
              <ErrorBanner message={err} />
            </div>
          )}

          {q && !loading && results.length === 0 && !err && (
            <div className="mt-12 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <p className="text-gray-500 text-lg">Không tìm thấy kết quả cho "{q}"</p>
            </div>
          )}

          {results.length > 0 && (
            <div className="mt-8 space-y-4">
              <div className="text-sm font-medium text-gray-600 mb-4">
                Tìm thấy {results.length} sinh viên
              </div>
              {results.map((student) => (
                <StudentCard key={student.student_id} student={student} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-300 py-8 mt-16">
        <div className="max-w-6xl mx-auto px-6 text-center">
          <p className="text-sm">
            © 2024 Hệ Thống Tra Cứu Sinh Viên. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

// Status Item Component
function StatusItem({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10">
      <span className="text-sm">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${active ? 'bg-green-400' : 'bg-red-400'}`}></span>
        <span className="text-xs font-medium">{active ? 'Active' : 'Inactive'}</span>
      </div>
    </div>
  );
}

// Student Card Component
function StudentCard({ student }: { student: MySQLStudent }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="group bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border border-slate-200">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-full font-bold text-sm">
              {student.full_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">{student.full_name}</h3>
              <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-xs rounded-full font-mono font-semibold">
                {student.mssv}
              </span>
            </div>
          </div>

          {/* Links */}
          {student.links && student.links.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
                Tham gia {student.links.length} chương trình
              </div>
              
              <div className={`space-y-3 ${expanded ? '' : 'max-h-48 overflow-hidden relative'}`}>
                {(() => {
                  const links = [...student.links].sort((a, b) => {
                    const ga = (a.gid || a.sheet_name || '').toString();
                    const gb = (b.gid || b.sheet_name || '').toString();
                    if (ga === gb) return (a.row_number || 0) - (b.row_number || 0);
                    return ga.localeCompare(gb, undefined, { sensitivity: 'base' });
                  });

                  const groups: Record<string, typeof links> = {};
                  for (const l of links) {
                    const key = (l.gid || l.sheet_name || 'Unknown').toString();
                    groups[key] = groups[key] || [];
                    groups[key].push(l);
                  }

                  return Object.keys(groups).map((gid) => (
                    <div key={gid} className="bg-white rounded-xl p-4 border border-slate-200">
                      <div className="text-xs font-semibold text-gray-500 uppercase mb-2">{gid}</div>
                      <div className="space-y-2">
                        {groups[gid].map((link) => {
                          const titleLabel = link.title && link.title.length > 100
                            ? `${link.title.slice(0, 100)}…`
                            : link.title || link.sheet_name || 'Unknown Sheet';

                          return (
                            <div key={link.link_id} className="pl-3 border-l-2 border-blue-400">
                              <div className="flex items-start gap-2">
                                <svg className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                                <div className="flex-1">
                                  {link.url ? (
                                    <a
                                      href={link.url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      title={link.title || ''}
                                      className="text-sm font-medium text-blue-700 hover:text-blue-900 hover:underline"
                                    >
                                      {titleLabel}
                                    </a>
                                  ) : (
                                    <span className="text-sm font-medium text-gray-800" title={link.title || ''}>{titleLabel}</span>
                                  )}

                                  {link.row_number && (
                                    <span className="text-gray-400 ml-2 text-xs">Row {link.row_number}</span>
                                  )}

                                  {link.sheet_name && link.sheet_name !== titleLabel && (
                                    <div className="text-xs text-gray-500 mt-1">{link.sheet_name}</div>
                                  )}

                                  {link.snippet && (
                                    <div className="text-gray-600 text-xs mt-1 line-clamp-2">{link.snippet}</div>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ));
                })()}
                
                {!expanded && student.links.length > 2 && (
                  <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-white to-transparent"></div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Expand Button */}
        {student.links && student.links.length > 2 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex-shrink-0 px-4 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg font-medium transition-colors"
          >
            {expanded ? '▲ Thu gọn' : '▼ Xem thêm'}
          </button>
        )}
      </div>
    </div>
  );
}
