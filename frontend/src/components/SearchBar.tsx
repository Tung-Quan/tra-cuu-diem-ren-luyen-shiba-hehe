// src/components/SearchBar.tsx
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function SearchBar() {
  const [sp] = useSearchParams();
  const navigate = useNavigate();
  const [q, setQ] = useState(sp.get("q") || "");

  useEffect(() => {
    const id = setTimeout(() => {
      const next = new URLSearchParams(sp);
      if (q) next.set("q", q);
      else next.delete("q");
      
      // Always stay on the landing page
      navigate({ pathname: "/", search: next.toString() }, { replace: true });
    }, 400);
    return () => clearTimeout(id);
  }, [q, navigate, sp]);

  return (
    <div className="relative">
      <form onSubmit={(e) => e.preventDefault()} className="relative">
        <div className="relative flex items-center">
          <svg 
            className="absolute left-4 w-5 h-5 text-gray-400"
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            className="w-full pl-12 pr-4 py-4 text-lg rounded-2xl border-2 border-gray-200 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-100 transition-all"
            placeholder="Tìm kiếm theo tên hoặc MSSV (tối thiểu 2 ký tự)..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
      </form>
    </div>
  );
}
