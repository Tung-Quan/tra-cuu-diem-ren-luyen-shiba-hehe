// src/components/SearchBar.tsx
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams, useLocation } from "react-router-dom";

export default function SearchBar() {
  const [sp] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [q, setQ] = useState(sp.get("q") || "");

  useEffect(() => {
    const id = setTimeout(() => {
      const next = new URLSearchParams(sp);
      if (q) next.set("q", q);
      else next.delete("q");
      
      // Giữ nguyên current route thay vì luôn redirect về /search
      const currentPath = location.pathname;
      const targetPath = currentPath === "/" ? "/search" : currentPath;
      
      navigate({ pathname: targetPath, search: next.toString() }, { replace: true });
    }, 400);
    return () => clearTimeout(id);
  }, [q, location.pathname, navigate, sp]);

  return (
    <div className="card">
      <form onSubmit={(e) => e.preventDefault()} className="flex gap-2 items-center">
        <input
          className="input"
          placeholder="Nhập từ khóa (tối thiểu 2 ký tự)…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
      </form>
    </div>
  );
}
