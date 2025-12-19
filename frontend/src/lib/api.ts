// src/lib/api.ts
import axios, { type AxiosRequestConfig } from "axios";

// ===== Axios instance =====
const BASE_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";

// Bạn vẫn có thể cấu hình timeout toàn cục qua env; nếu không đặt, mặc định 20000ms
const DEFAULT_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT ?? 20000);

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: DEFAULT_TIMEOUT,
});

// ===== Types =====
export type HealthResponse = {
  status: string;
  database_rows: number;
  sheets: string[];
  links: {
    total: number;
    unique_urls: number;
  };
  mysql_available: boolean;
  gspread_available: boolean;
  google_api_available: boolean;
  deep_scan: boolean;
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

export type DBStatsResponse = {
  ok: boolean;
  students: number;
  links: number;
  connections: number;
  students_with_links: number;
  top_students?: Array<{ full_name: string; mssv: string; link_count: number }>;
  sheets?: string[];
};

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
export const getHealth = () => api.get<HealthResponse>("/api/admin/health");

// QUAN TRỌNG: TẮT TIMEOUT RIÊNG CHO /search (timeout: 0)
export function search(
  q: string,
  opts?: { follow_links?: boolean; link_limit?: number; top_k?: number }
) {
  const params: Record<string, string | number | boolean> = { q };
  if (opts?.follow_links !== undefined) params.follow_links = opts.follow_links;
  if (opts?.link_limit) params.link_limit = opts.link_limit;
  if (opts?.top_k) params.top_k = opts.top_k;

  // timeout: 0 => không timeout (axios)
  const cfg: AxiosRequestConfig = { params, timeout: 0 };
  return api.get<SearchResponse>("/api/search", cfg);
}

export function fetchPreview(url: string) {
  return api.get<FetchPreviewResponse>("/api/debug/check_url", { params: { u: url }, timeout: 0 });
}

// ===== MySQL API =====
export type MySQLStudent = {
  student_id: number;
  full_name: string;
  mssv: string;
  search_name: string;
  links: Array<{
    link_id: number;
    url: string;
    title?: string;
    sheet_name?: string;
    gid?: string;
    kind?: string;
    row_number?: number;
    snippet?: string;
  }>;
};

export type MySQLSearchResponse = {
  ok: boolean;
  query: string;
  results: MySQLStudent[];
  count: number;
  execution_time_ms: number;
};

export type MySQLCountResponse = {
  ok: boolean;
  count: number;
};

export function mysqlSearch(q: string, limit: number = 50) {
  return api.get<MySQLSearchResponse>("/api/mysql/students/search", { 
    params: { q, limit },
    timeout: 10000
  });
}

// ===== Add Link API =====
export type AddLinkRequest = {
  url: string;
};

export type AddLinkResponse = {
  ok: boolean;
  link?: {
    url: string;
    sheet: string;
    row: number;
    col: number;
    address: string;
    gid: string | null;
    sheet_name: string | null;
  };
  total_links?: number;
  message?: string;
  error?: string;
};

export function addLink(data: AddLinkRequest, setLoading?: (loading: boolean) => void) {
  // https://docs.google.com/spreadsheets/d/1-ypUyKglUjblgy1Gy0gITcdHF4YLdJnaCNKM_6_fCrI/edit?gid=29840804#gid=29840804 it can be this and only take the url after /d/[a-zA-Z0-9_-]+/ take the [a-zA-Z0-9_-]+/ part
  const id = data.url.match(/\/d\/([a-zA-Z0-9_-]+)\//)?.[1];

  //   'http://localhost:8000/api/admin/process-linked-sheets?spreadsheet_id=1-ypUyKglUjblgy1Gy0gITcdHF4YLdJnaCNKM_6_fCrI&dry_run=true&process_files=true' the standard API is a POST to /api/links/add with url parameter
  setLoading?.(true);
  return api.post<AddLinkResponse>("/api/admin/process-linked-sheets", null, {
    params: {
      spreadsheet_id: id,
      dry_run: true,
      process_files: true,
    },
  });
}
