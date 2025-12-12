// src/pages/AddLinkPage.tsx
import { useState } from "react";
import { addLink, type AddLinkRequest } from "../lib/api";
import ErrorBanner from "../components/ErrorBanner";

export default function AddLinkPage() {
  const [formData, setFormData] = useState<AddLinkRequest>({
    url: "",
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

    setLoading(true);
    try {
      const response = await addLink(formData, setLoading);
      if (response.data.ok) {
        setSuccess(response.data.message || "Link đã được thêm thành công!");
        // Reset form
        setFormData({ ...formData, url: "" });
      } else {
        setError(response.data.error || "Failed to add link");
      }
    } catch (err: unknown) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="grid gap-4">
        <div className="card">
          <h2 className="text-xl font-semibold">Đang thêm link...</h2>
        </div>
      </div>
    );
  }
  return (
    <div className="grid gap-4">
      <div className="card">
        <h1 className="text-2xl font-bold mb-2">Thêm Link Mới</h1>
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

    
      </form>

      
    </div>
  );
}
