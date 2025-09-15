// src/components/SearchBar.tsx
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function SearchBar() {
  const [sp, setSp] = useSearchParams();
  const navigate = useNavigate();
  const [q, setQ] = useState(sp.get("q") || "");

  useEffect(() => {
    const id = setTimeout(() => {
      const next = new URLSearchParams(sp);
      if (q) next.set("q", q);
      else next.delete("q");
      navigate({ pathname: "/search", search: next.toString() }, { replace: true });
    }, 400);
    return () => clearTimeout(id);
  }, [q]);

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
