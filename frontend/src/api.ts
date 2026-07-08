export interface Lead {
  id: number;
  place_key: string;
  name: string;
  main_category: string | null;
  categories: string[] | null;
  address: string | null;
  city: string | null;
  phone: string | null;
  website: string | null;
  rating: number | null;
  reviews_count: number | null;
  socials: Record<string, string> | null;
  source_query: string | null;
  scraped_at: string | null;
}

export interface LeadsResponse {
  total: number;
  page: number;
  page_size: number;
  items: Lead[];
}

export interface Job {
  id: number;
  type: string;
  params: { query?: string; city?: string; max_results?: number };
  status: string;
  progress: number;
  error: string | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface LeadFilters {
  city?: string;
  category?: string;
  has_website?: boolean;
  has_phone?: boolean;
  min_rating?: number;
  search?: string;
  sort?: string;
  order?: string;
  page?: number;
  page_size?: number;
}

export function buildQuery(filters: Record<string, unknown>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "" && value !== null) {
      params.set(key, String(value));
    }
  }
  return params.toString();
}

export async function fetchLeads(filters: LeadFilters): Promise<LeadsResponse> {
  const res = await fetch(`/api/leads?${buildQuery(filters as Record<string, unknown>)}`);
  if (!res.ok) throw new Error(`leads fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchJobs(): Promise<{ items: Job[] }> {
  const res = await fetch("/api/jobs?limit=25");
  if (!res.ok) throw new Error(`jobs fetch failed: ${res.status}`);
  return res.json();
}

export async function createJob(body: {
  query: string;
  city?: string;
  max_results?: number;
}): Promise<Job> {
  const res = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`job create failed: ${res.status}`);
  return res.json();
}

export function exportCsvUrl(filters: LeadFilters): string {
  const { sort, order, page, page_size, ...rest } = filters;
  void sort;
  void order;
  void page;
  void page_size;
  return `/api/export.csv?${buildQuery(rest as Record<string, unknown>)}`;
}
