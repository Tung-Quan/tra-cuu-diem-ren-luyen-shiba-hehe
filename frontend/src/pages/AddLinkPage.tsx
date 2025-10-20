// src/pages/AddLinkPage.tsx
import { useState } from "react";
import { addLink, type AddLinkRequest } from "../lib/api";
import ErrorBanner from "../components/ErrorBanner";

export default function AddLinkPage() {
  const [formData, setFormData] = useState<AddLinkRequest>({
    url: "",
    sheet: "HỌC KỲ 2",
    row: 1,
    col: 1,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [success, setSuccess] = useState<string>();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(undefined);
    setSuccess(undefined);

    // Validate
    if (!formData.url || !formData.url.startsWith("http")) {
      setError("URL phải bắt đầu bằng http:// hoặc https://");
      return;
    }

    if (!formData.sheet) {
      setError("Vui lòng chọn sheet");
      return;
    }

    if (formData.row < 1) {
      setError("Row phải >= 1");
      return;
    }

    setLoading(true);
    try {
      const response = await addLink(formData);
      if (response.data.ok) {
        setSuccess(response.data.message || "Link đã được thêm thành công!");
        // Reset form
        setFormData({ ...formData, url: "" });
      } else {
        setError(response.data.error || "Failed to add link");
      }
    } catch (err: any) {
      setError(err?.response?.data?.error || String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-4 max-w-2xl mx-auto">
      <div className="card">
        <h1 className="text-2xl font-bold mb-2">➕ Thêm Link Mới</h1>
        <p className="text-sm text-gray-600">
          Thêm đường link vào LINK_POOL để có thể tìm kiếm trong nội dung
        </p>
      </div>

      {error && <ErrorBanner message={error} />}
      
      {success && (
        <div className="card bg-green-50 border-l-4 border-green-500">
          <div className="flex items-center gap-2">
            <span className="text-2xl">✅</span>
            <span className="text-green-800 font-medium">{success}</span>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-4">
        {/* URL Input */}
        <div>
          <label className="block text-sm font-medium mb-1">
            URL <span className="text-red-500">*</span>
          </label>
          <input
            type="url"
            className="input w-full"
            placeholder="https://docs.google.com/spreadsheets/d/..."
            value={formData.url}
            onChange={(e) => setFormData({ ...formData, url: e.target.value })}
            required
          />
          <p className="text-xs text-gray-500 mt-1">
            Google Sheets, Drive, hoặc bất kỳ URL nào
          </p>
        </div>

        {/* Sheet Name */}
        <div>
          <label className="block text-sm font-medium mb-1">
            Sheet Name <span className="text-red-500">*</span>
          </label>
          <select
            className="input w-full"
            value={formData.sheet}
            onChange={(e) => setFormData({ ...formData, sheet: e.target.value })}
            required
          >
            <option value="HỌC KỲ 2">HỌC KỲ 2</option>
            <option value="CTV HK2">CTV HK2</option>
            <option value="HỌC KỲ 1">HỌC KỲ 1</option>
            <option value="CTV HK1">CTV HK1</option>
            <option value="Custom">Custom (nhập bên dưới)</option>
          </select>
          
          {formData.sheet === "Custom" && (
            <input
              type="text"
              className="input w-full mt-2"
              placeholder="Nhập tên sheet..."
              onChange={(e) => setFormData({ ...formData, sheet: e.target.value })}
            />
          )}
        </div>

        {/* Row & Col */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">
              Row (Dòng) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              className="input w-full"
              min={1}
              value={formData.row}
              onChange={(e) => setFormData({ ...formData, row: Number(e.target.value) })}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Column (Cột)
            </label>
            <input
              type="number"
              className="input w-full"
              min={1}
              value={formData.col}
              onChange={(e) => setFormData({ ...formData, col: Number(e.target.value) })}
            />
            <p className="text-xs text-gray-500 mt-1">
              1 = A, 2 = B, 3 = C, ...
            </p>
          </div>
        </div>

        {/* Preview */}
        <div className="bg-gray-50 p-3 rounded text-sm">
          <div className="font-medium mb-2">📋 Preview:</div>
          <div className="space-y-1 text-gray-700">
            <div><span className="font-medium">Sheet:</span> {formData.sheet}</div>
            <div><span className="font-medium">Cell:</span> {String.fromCharCode(64 + (formData.col || 1))}{formData.row}</div>
            <div><span className="font-medium">URL:</span> {formData.url || "(chưa nhập)"}</div>
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={loading || !formData.url}
        >
          {loading ? "⏳ Đang thêm..." : "➕ Thêm Link"}
        </button>
      </form>

      {/* Info Box */}
      <div className="card bg-blue-50">
        <div className="font-medium mb-2">💡 Lưu ý:</div>
        <ul className="text-sm text-gray-700 space-y-1 list-disc ml-5">
          <li>Link sẽ được thêm vào LINK_POOL trong bộ nhớ</li>
          <li>Nếu có MySQL, link cũng sẽ được sync vào database</li>
          <li>Link có thể được tìm kiếm qua /search với follow_links=true</li>
          <li>Hỗ trợ Google Sheets, Drive, và các URL khác</li>
        </ul>
      </div>
    </div>
  );
}
