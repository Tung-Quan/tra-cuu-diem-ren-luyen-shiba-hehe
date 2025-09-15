// src/components/SheetSummaryList.tsx
type SheetSummaryItem = { sheet: string; count: number };

export default function SheetSummaryList({ items }: { items: SheetSummaryItem[] }) {
  if (!items?.length) return null;
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-3">Tổng hợp theo Sheet</h3>
      <ul className="grid md:grid-cols-2 gap-3">
        {items.map((s, idx) => (
          <li key={idx} className="p-3 border rounded-xl bg-white">
            <div className="flex items-center justify-between">
              <div className="font-medium">{s.sheet}</div>
              <span className="badge">{s.count} kết quả</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
