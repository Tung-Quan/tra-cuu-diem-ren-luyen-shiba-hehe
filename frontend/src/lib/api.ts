// src/lib/api.ts
import axios, { type AxiosRequestConfig, type AxiosResponse } from "axios";

// ===== Axios instance =====
const BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta as any).env?.REACT_APP_API_URL ||
  "http://127.0.0.1:8000";

// Bạn vẫn có thể cấu hình timeout toàn cục qua env; nếu không đặt, mặc định 20000ms
const DEFAULT_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT ?? 20000);

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: DEFAULT_TIMEOUT,
});

// ===== Types =====
export type HealthResponse = {
  ok: boolean;
  rows: number;
  sheets: number;
  links: number;
};

export type Hit = {
  sheet: string;
  row: number;
  snippet: string;
  snippet_nodau?: string;
  links: string[];
  score: number;
};

export type LinkHit = {
  url: string;
  snippet: string;
  snippet_nodau?: string;
};

export type SearchResponse = {
  query: string;
  hits: Hit[];
  link_hits?: LinkHit[];
};

export type SheetsResponse = { sheets: string[] };

export type FetchPreviewResponse = {
  kind: "docs" | "sheets" | "unknown";
  file_id?: string;
  gid?: string;
  export_candidates: string[];
  was_marked?: string;
  now_marked?: string;
  fetched: boolean;
  snippet?: string;
};

// ===== Helpers =====
export const isAxiosTimeout = (e: unknown): boolean =>
  axios.isAxiosError(e) && e.code === "ECONNABORTED";

// (tuỳ chọn) tạo AxiosResponse giả khi muốn nuốt lỗi mà vẫn trả response
function fakeResponse<T>(config: AxiosRequestConfig, data: T): AxiosResponse<T> {
  return {
    data,
    status: 200,
    statusText: "OK (timeout ignored)",
    headers: {},
    config,
  };
}

// ===== (tuỳ chọn) Interceptor: NUỐT timeout toàn cục =====
// Bật nếu bạn muốn mọi request tự động bỏ qua timeout, thay vì throw.
// api.interceptors.response.use(
//   (r) => r,
//   (error) => {
//     if (isAxiosTimeout(error)) {
//       const cfg = error.config ?? {};
//       // Nếu là /search, trả về payload rỗng đúng schema:
//       if (cfg.url?.includes("/search")) {
//         const q = (cfg.params as any)?.q ?? "";
//         return Promise.resolve(
//           fakeResponse(cfg, { query: q, hits: [], link_hits: [] } as SearchResponse)
//         );
//       }
//       // Các API khác: trả 204/OK rỗng
//       return Promise.resolve(fakeResponse(cfg, null as any));
//     }
//     return Promise.reject(error);
//   }
// );

// ===== API helpers =====
export const getHealth = () => api.get<HealthResponse>("/health");

// QUAN TRỌNG: TẮT TIMEOUT RIÊNG CHO /search (timeout: 0)
export function search(
  q: string,
  opts?: { follow_links?: boolean; link_limit?: number; top_k?: number }
) {
  const params: any = { q };
  if (opts?.follow_links !== undefined) params.follow_links = opts.follow_links;
  if (opts?.link_limit) params.link_limit = opts.link_limit;
  if (opts?.top_k) params.top_k = opts.top_k;

  // timeout: 0 => không timeout (axios)
  const cfg: AxiosRequestConfig = { params, timeout: 0 };
  return api.get<SearchResponse>("/search", cfg);
}

export function fetchPreview(url: string) {
  return api.get<FetchPreviewResponse>("/debug/check_url", { params: { u: url }, timeout: 0 });
}
