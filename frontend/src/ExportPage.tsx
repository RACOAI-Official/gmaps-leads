import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { exportCsvUrl, fetchLeads, type LeadFilters } from "./api.ts";

const ALL_COLUMNS = [
  "id",
  "name",
  "main_category",
  "address",
  "city",
  "phone",
  "website",
  "rating",
  "reviews_count",
  "source_query",
  "scraped_at",
];
const DEFAULT_COLUMNS = new Set(["name", "main_category", "city", "phone", "website", "rating"]);

export function ExportPage() {
  const [filters, setFilters] = useState<LeadFilters>({});
  const [columns, setColumns] = useState<Set<string>>(new Set(DEFAULT_COLUMNS));
  const [includeScore, setIncludeScore] = useState(false);
  const [includeEnrichment, setIncludeEnrichment] = useState(false);

  const { data: countData } = useQuery({
    queryKey: ["export-count", filters],
    queryFn: () => fetchLeads({ ...filters, page_size: 1 }),
  });
  const count = countData?.total ?? null;

  function toggleColumn(col: string) {
    setColumns((prev) => {
      const next = new Set(prev);
      if (next.has(col)) next.delete(col);
      else next.add(col);
      return next;
    });
  }

  const href = exportCsvUrl(filters, {
    columns: Array.from(columns),
    include_score: includeScore,
    include_enrichment: includeEnrichment,
  });

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Export leads</h3>
        <div className="right">
          <a className="btn" href={href}>
            Download CSV ({count != null ? count.toLocaleString() : "…"} rows)
          </a>
        </div>
      </div>

      <div className="export-grid">
        <div className="settings-section">
          <div className="settings-section-head">
            <h4>Filters</h4>
          </div>
          <div className="settings-body">
            <label className="field">
              <span>Search</span>
              <input
                placeholder="name / address"
                defaultValue={filters.search ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value || undefined }))}
              />
            </label>
            <label className="field">
              <span>City</span>
              <input
                placeholder="Dhaka"
                defaultValue={filters.city ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, city: e.target.value || undefined }))}
              />
            </label>
            <label className="field">
              <span>Category</span>
              <input
                placeholder="hospital"
                defaultValue={filters.category ?? ""}
                onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value || undefined }))}
              />
            </label>
            <label className="field">
              <span>Min rating</span>
              <select
                value={filters.min_rating ?? ""}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, min_rating: e.target.value ? Number(e.target.value) : undefined }))
                }
              >
                <option value="">any</option>
                <option value="3">3+</option>
                <option value="4">4+</option>
                <option value="4.5">4.5+</option>
              </select>
            </label>
            <div className="check-row">
              <label className="check">
                <input
                  type="checkbox"
                  checked={filters.has_website ?? false}
                  onChange={(e) => setFilters((f) => ({ ...f, has_website: e.target.checked || undefined }))}
                />
                has website
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={filters.has_phone ?? false}
                  onChange={(e) => setFilters((f) => ({ ...f, has_phone: e.target.checked || undefined }))}
                />
                has phone
              </label>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <div className="settings-section-head">
            <h4>Columns</h4>
            <button className="link-btn" onClick={() => setColumns(new Set(ALL_COLUMNS))}>
              all
            </button>
            <button className="link-btn" onClick={() => setColumns(new Set())}>
              none
            </button>
          </div>
          <div className="settings-body column-grid">
            {ALL_COLUMNS.map((col) => (
              <label className="check" key={col}>
                <input type="checkbox" checked={columns.has(col)} onChange={() => toggleColumn(col)} />
                {col}
              </label>
            ))}
          </div>
          <div className="settings-section-head" style={{ marginTop: 8 }}>
            <h4>Extra data</h4>
          </div>
          <div className="settings-body">
            <label className="check">
              <input type="checkbox" checked={includeScore} onChange={(e) => setIncludeScore(e.target.checked)} />
              include score + AI flag
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={includeEnrichment}
                onChange={(e) => setIncludeEnrichment(e.target.checked)}
              />
              include enrichment (emails, socials, tech)
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
