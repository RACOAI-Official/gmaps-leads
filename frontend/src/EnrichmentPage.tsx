import { useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  createEnrichJob,
  fetchEnrichments,
  type Enrichment,
  type EnrichmentFilters,
} from "./api.ts";
import { ChevronLeft, ChevronRight } from "./icons.tsx";

const columnHelper = createColumnHelper<Enrichment>();

const STATUS_LABEL: Record<string, string> = {
  ok: "enriched",
  empty: "no data",
  failed: "failed",
  needs_browser: "needs browser",
};

const columns = [
  columnHelper.accessor("name", { header: "Name" }),
  columnHelper.accessor("website", {
    header: "Website",
    cell: (c) =>
      c.getValue() ? (
        <a href={c.getValue()!} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
          link
        </a>
      ) : (
        <span className="muted">—</span>
      ),
  }),
  columnHelper.accessor("status", {
    header: "Status",
    cell: (c) => {
      const s = c.getValue();
      if (!s) return <span className="muted">pending</span>;
      return <span className={`status-chip status-chip-${s}`}>{STATUS_LABEL[s] ?? s}</span>;
    },
  }),
  columnHelper.accessor("emails", {
    header: "Emails",
    cell: (c) => {
      const e = c.getValue();
      return e && e.length ? e.length : <span className="muted">—</span>;
    },
  }),
  columnHelper.accessor("socials", {
    header: "Socials",
    cell: (c) => {
      const s = c.getValue();
      const n = s ? Object.keys(s).length : 0;
      return n ? n : <span className="muted">—</span>;
    },
  }),
  columnHelper.accessor("tech_stack", {
    header: "Tech",
    cell: (c) => {
      const t = c.getValue();
      return t && t.length ? (
        t.map((x) => (
          <span key={x} className="tag">
            {x}
          </span>
        ))
      ) : (
        <span className="muted">—</span>
      );
    },
  }),
  columnHelper.accessor("crawled_at", {
    header: "Crawled",
    cell: (c) =>
      c.getValue() ? new Date(c.getValue()!).toLocaleDateString() : <span className="muted">—</span>,
  }),
];

const PAGE_SIZE = 25;

function pageList(current: number, max: number): (number | "…")[] {
  if (max <= 7) return Array.from({ length: max }, (_, i) => i + 1);
  const out: (number | "…")[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(max - 1, current + 1);
  if (start > 2) out.push("…");
  for (let i = start; i <= end; i++) out.push(i);
  if (end < max - 1) out.push("…");
  out.push(max);
  return out;
}

export function EnrichmentPage() {
  const qc = useQueryClient();
  const [filters, setFilters] = useState<EnrichmentFilters>({ page: 1, page_size: PAGE_SIZE });
  const [max, setMax] = useState(50);

  const { data, isFetching } = useQuery({
    queryKey: ["enrichments", filters],
    queryFn: () => fetchEnrichments(filters),
    placeholderData: keepPreviousData,
  });

  const enrichMutation = useMutation({
    mutationFn: () => createEnrichJob({ max }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["enrichments"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const rows = useMemo(() => data?.items ?? [], [data]);
  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  const total = data?.total ?? 0;
  const page = filters.page ?? 1;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function patch(next: Partial<EnrichmentFilters>) {
    setFilters((f) => ({ ...f, ...next, page: 1 }));
  }
  function goTo(p: number) {
    setFilters((f) => ({ ...f, page: p }));
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Enrichment</h3>
        <div className="right">
          <input
            type="number"
            value={max}
            min={1}
            max={500}
            onChange={(e) => setMax(Number(e.target.value))}
            style={{ width: 90 }}
            title="Max businesses to enrich per job"
          />
          <button
            className="btn"
            disabled={enrichMutation.isPending}
            onClick={() => enrichMutation.mutate()}
          >
            {enrichMutation.isPending ? "Queuing…" : "Enrich pending"}
          </button>
        </div>
      </div>

      {enrichMutation.isSuccess && (
        <div className="notice">
          Enrichment job #{enrichMutation.data.id} queued — watch the Jobs tab. The worker
          crawls each site in a browser session, so it may take a few minutes.
        </div>
      )}

      <div className="toolbar">
        <input
          placeholder="Search name / website…"
          defaultValue={filters.search ?? ""}
          onKeyDown={(e) => {
            if (e.key === "Enter") patch({ search: (e.target as HTMLInputElement).value });
          }}
        />
        <input
          placeholder="City"
          defaultValue={filters.city ?? ""}
          onKeyDown={(e) => {
            if (e.key === "Enter") patch({ city: (e.target as HTMLInputElement).value });
          }}
        />
        <select
          value={filters.status ?? ""}
          onChange={(e) => patch({ status: e.target.value || undefined })}
        >
          <option value="">any status</option>
          <option value="ok">enriched</option>
          <option value="empty">no data</option>
          <option value="failed">failed</option>
          <option value="needs_browser">needs browser</option>
        </select>
        <span className="count">{isFetching ? "…" : `${total} sites`}</span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id}>{flexRender(h.column.columnDef.header, h.getContext())}</th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && !isFetching && (
              <tr>
                <td colSpan={columns.length} className="muted">
                  No enrichment data yet. Click <strong>Enrich pending</strong> to crawl websites
                  for emails, socials, and tech stack.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <button className="page-pill nav" disabled={page <= 1} onClick={() => goTo(page - 1)}>
          <ChevronLeft />
        </button>
        {pageList(page, maxPage).map((p, i) =>
          p === "…" ? (
            <span key={`e${i}`} className="page-ellipsis">
              …
            </span>
          ) : (
            <button
              key={p}
              className={`page-pill ${p === page ? "active" : ""}`}
              onClick={() => goTo(p)}
            >
              {p}
            </button>
          ),
        )}
        <button className="page-pill nav" disabled={page >= maxPage} onClick={() => goTo(page + 1)}>
          <ChevronRight />
        </button>
      </div>
    </div>
  );
}
