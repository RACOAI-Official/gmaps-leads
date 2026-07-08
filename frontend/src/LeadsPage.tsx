import { useMemo, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  exportCsvUrl,
  fetchLeads,
  type Lead,
  type LeadFilters,
} from "./api.ts";
import { LeadDrawer } from "./LeadDrawer.tsx";

const columnHelper = createColumnHelper<Lead>();

const columns = [
  columnHelper.accessor("name", { header: "Name" }),
  columnHelper.accessor("main_category", { header: "Category" }),
  columnHelper.accessor("city", { header: "City" }),
  columnHelper.accessor("phone", { header: "Phone" }),
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
  columnHelper.accessor("rating", { header: "Rating" }),
  columnHelper.accessor("reviews_count", { header: "Reviews" }),
];

const PAGE_SIZE = 50;

export function LeadsPage() {
  const [filters, setFilters] = useState<LeadFilters>({
    sort: "scraped_at",
    order: "desc",
    page: 1,
    page_size: PAGE_SIZE,
  });
  const [selected, setSelected] = useState<Lead | null>(null);

  const { data, isFetching } = useQuery({
    queryKey: ["leads", filters],
    queryFn: () => fetchLeads(filters),
    placeholderData: keepPreviousData,
  });

  const rows = useMemo(() => data?.items ?? [], [data]);

  const table = useReactTable({
    data: rows,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
  });

  const total = data?.total ?? 0;
  const page = filters.page ?? 1;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function patch(next: Partial<LeadFilters>) {
    setFilters((f) => ({ ...f, ...next, page: 1 }));
  }

  function toggleSort(colId: string) {
    setFilters((f) => ({
      ...f,
      sort: colId,
      order: f.sort === colId && f.order === "asc" ? "desc" : "asc",
      page: 1,
    }));
  }

  return (
    <>
      <div className="toolbar">
        <input
          placeholder="Search name / address…"
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
        <input
          placeholder="Category"
          defaultValue={filters.category ?? ""}
          onKeyDown={(e) => {
            if (e.key === "Enter") patch({ category: (e.target as HTMLInputElement).value });
          }}
        />
        <label className="check">
          <input
            type="checkbox"
            checked={filters.has_website ?? false}
            onChange={(e) => patch({ has_website: e.target.checked || undefined })}
          />
          has website
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={filters.has_phone ?? false}
            onChange={(e) => patch({ has_phone: e.target.checked || undefined })}
          />
          has phone
        </label>
        <select
          value={filters.min_rating ?? ""}
          onChange={(e) =>
            patch({ min_rating: e.target.value ? Number(e.target.value) : undefined })
          }
        >
          <option value="">any rating</option>
          <option value="3">3+</option>
          <option value="4">4+</option>
          <option value="4.5">4.5+</option>
        </select>
        <a className="btn secondary" href={exportCsvUrl(filters)}>
          Export CSV
        </a>
        <span className="count">
          {isFetching ? "…" : `${total} leads`}
        </span>
      </div>

      <div style={{ overflowX: "auto" }}>
        <table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id} onClick={() => toggleSort(h.column.id)}>
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {filters.sort === h.column.id
                      ? filters.order === "asc"
                        ? " ▲"
                        : " ▼"
                      : ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} onClick={() => setSelected(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && !isFetching && (
              <tr>
                <td colSpan={columns.length} className="muted">
                  No leads match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pager">
        <button
          className="btn secondary"
          disabled={page <= 1}
          onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) - 1 }))}
        >
          Prev
        </button>
        <span>
          Page {page} / {maxPage}
        </span>
        <button
          className="btn secondary"
          disabled={page >= maxPage}
          onClick={() => setFilters((f) => ({ ...f, page: (f.page ?? 1) + 1 }))}
        >
          Next
        </button>
      </div>

      {selected && <LeadDrawer lead={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
