// src/pages/SearchPage.tsx
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { search } from "../lib/api";
import type { SearchResponse, Hit } from "../lib/api";
import { isAxiosTimeout } from "../lib/api";
import SearchBar from "../components/SearchBar";
import SheetSummaryList from "../components/SheetSummaryList";
import Loading from "../components/Loading";
import ErrorBanner from "../components/ErrorBanner";
import ResultCard from "../components/ResultCard";
import FetchPreview from "../components/FetchPreview";

type SheetSummaryItem = { sheet: string; count: number };

export default function SearchPage() {
  const [sp] = useSearchParams();
  const q = (sp.get("q") || "").trim();
  const [data, setData] = useState<SearchResponse>();
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>();
  const [followLinks, setFollowLinks] = useState(true);
  const [linkLimit, setLinkLimit] = useState(100);
  const [topK, setTopK] = useState(50);

  useEffect(() => {
    setErr(undefined);
    setData(undefined);
    if (!q || q.length < 2) return;

    setLoading(true);
    search(q, { follow_links: followLinks, link_limit: linkLimit, top_k: topK })
      .then((r) => setData(r.data))
      .catch((e) => {
        // BỎ QUA TIMEOUT: không hiển thị lỗi, chỉ dừng loading
        if (isAxiosTimeout(e)) {
          // (tuỳ chọn) vẫn setData về rỗng để UI có trạng thái xác định:
          setData({ query: q, hits: [], link_hits: [] });
          return;
        }
        setErr(e?.response?.data?.error || String(e));
      })
      .finally(() => setLoading(false));
  }, [q, followLinks, linkLimit, topK]);

  const sheetSummary: SheetSummaryItem[] = useMemo(() => {
    const map = new Map<string, number>();
    (data?.hits || []).forEach((h) => map.set(h.sheet, (map.get(h.sheet) || 0) + 1));
    return Array.from(map.entries())
      .map(([sheet, count]) => ({ sheet, count }))
      .sort((a, b) => b.count - a.count);
  }, [data?.hits]);

  return (
    <div className="grid gap-4">
      <SearchBar />
      <FetchPreview />

      {q && (
        <div className="text-sm text-gray-600">
          Từ khóa: <span className="font-medium">{q}</span>
        </div>
      )}

      <div className="flex items-center gap-4 flex-wrap">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={followLinks} onChange={(e) => setFollowLinks(e.target.checked)} />
          <span>Quét nội dung các link liên kết</span>
        </label>

        <label className="text-sm flex items-center gap-2">
          <span>Link limit: {linkLimit}</span>
          <input aria-label="link-limit" type="range" min={10} max={200} value={linkLimit} onChange={(e) => setLinkLimit(Number(e.target.value))} />
        </label>

        <label className="text-sm flex items-center gap-2">
          <span>Top K: {topK}</span>
          <input aria-label="top-k" type="range" min={10} max={200} value={topK} onChange={(e) => setTopK(Number(e.target.value))} />
        </label>
      </div>

      {loading && <Loading />}
      {err && <ErrorBanner message={err} />}

      {!!sheetSummary.length && <SheetSummaryList items={sheetSummary} />}

      {!!data?.hits?.length && (
        <div className="grid gap-3">
          {data!.hits!.map((r: Hit, idx: number) => (
            <ResultCard key={idx} r={r} />
          ))}
        </div>
      )}

      {data?.link_hits && (
        <div className="card">
          <div className="font-medium">Kết quả trong tài liệu liên kết</div>
          <div className="mt-2 space-y-2">
            {data.link_hits.map((lr, i) => (
              <div key={i} className="p-2 border rounded">
                <div className="text-sm break-all"><strong>{lr.url}</strong></div>
                <pre className="mt-1 text-xs bg-slate-50 p-2 rounded overflow-auto whitespace-pre-wrap">
                  {lr.snippet}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {q && !loading && !err && (!data?.hits?.length && !data?.link_hits?.length) && (
        <div className="card">Không có kết quả phù hợp.</div>
      )}
    </div>
  );
}
