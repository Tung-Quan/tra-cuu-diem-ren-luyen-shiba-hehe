// src/pages/LandingPage.tsx
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { mysqlSearch, getDbStats, type MySQLStudent, type DBStatsResponse } from "../lib/api";
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
  const [statsData, setStatsData] = useState<DBStatsResponse>();

  // Load stats data on mount
  useEffect(() => {
    getDbStats()
      .then(r => setStatsData(r.data))
      .catch(() => { });
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
        {/* Background logo (place frontend/public/logo.png) */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-10">
          <img src="/Logo_ULaw.png" alt="Background logo" className="max-w-xs" />
        </div>

        <div className="relative z-10 max-w-7xl mx-auto px-6 py-16">
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

          {/* Database Statistics Cards */}
          {statsData && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{statsData.students.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Total Students</div>
              </div>

              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{statsData.links.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Total Links</div>
              </div>

              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{statsData.connections.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Connections</div>
              </div>

              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
                <div className="text-3xl font-bold mb-1">{statsData.students_with_links.toLocaleString()}</div>
                <div className="text-sm text-slate-300">Students with Links</div>
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
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm">
              © 2024 Hệ Thống Tra Cứu Sinh Viên. All rights reserved.
            </p>
            <div className="flex items-center gap-6">
              <a
                href="/contact"
                className="text-sm hover:text-white transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Liên Hệ & Hỗ Trợ
              </a>
              <a
                href="https://buymeacoffee.com/tungquan32w"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm hover:text-yellow-400 transition-colors flex items-center gap-2"
              >
                ☕ Ủng Hộ
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Student Card Component
function StudentCard({ student }: { student: MySQLStudent }) {
  return (
    <div className="group bg-gradient-to-br from-white to-slate-50 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 p-6 border border-slate-200">
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

              <div className="space-y-3">
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
              </div>
            </div>
          )}
        </div>
    </div>
  );
}
