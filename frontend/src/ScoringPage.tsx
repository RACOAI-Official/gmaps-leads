import { useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import {
  createScoreJob,
  fetchScores,
  type ScoredLead,
  type ScoreFilters,
} from "./api.ts";
import { ChevronLeft, ChevronRight } from "./icons.tsx";

const columnHelper = createColumnHelper<ScoredLead>();

function scoreClass(score: number | null): string {
  if (score == null) return "score-none";
  if (score >= 70) return "score-hi";
  if (score >= 40) return "score-med";
  return "score-low";
}

const columns = [
  columnHelper.accessor("name", { header: "Name" }),
  columnHelper.accessor("main_category", {
    header: "Category",
    cell: (c) => c.getValue() ?? <span className="muted">—</span>,
  }),
  columnHelper.accessor("city", {
    header: "City",
    cell: (c) => c.getValue() ?? <span className="muted">—</span>,
  }),
  columnHelper.accessor("rating", {
    header: "Rating",
    cell: (c) =>
      c.getValue() != null ? (
        <span className="rating-chip">
          <span className="star">★</span>
          {c.getValue()}
        </span>
      ) : (
        <span className="muted">—</span>
      ),
  }),
  columnHelper.accessor("score", {
    header: "Score",
    cell: (c) => {
      const s = c.getValue();
      return <span className={`score-chip ${scoreClass(s)}`}>{s ?? "—"}</span>;
    },
  }),
  columnHelper.accessor("has_llm", {
    header: "AI",
    cell: (c) =>
      c.getValue() ? <span className="tag tag-accent">explained</span> : <span className="muted">—</span>,
  }),
  columnHelper.accessor("scored_at", {
    header: "Scored",
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

export function ScoringPage() {
  const qc = useQueryClient();
  const [filters, setFilters] = useState<ScoreFilters>({ page: 1, page_size: PAGE_SIZE });
  const [explain, setExplain] = useState(true);
  const [max, setMax] = useState(100);
  const [selected, setSelected] = useState<ScoredLead | null>(null);

  const { data, isFetching } = useQuery({
    queryKey: ["scores", filters],
    queryFn: () => fetchScores(filters),
    placeholderData: keepPreviousData,
  });

  const scoreMutation = useMutation({
    mutationFn: () => createScoreJob({ max, explain }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scores"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const rows = useMemo(() => data?.items ?? [], [data]);
  const table = useReactTable({ data: rows, columns, getCoreRowModel: getCoreRowModel() });

  const total = data?.total ?? 0;
  const page = filters.page ?? 1;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

  function patch(next: Partial<ScoreFilters>) {
    setFilters((f) => ({ ...f, ...next, page: 1 }));
  }
  function goTo(p: number) {
    setFilters((f) => ({ ...f, page: p }));
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Lead Scoring</h3>
        <div className="right">
          <input
            type="number"
            value={max}
            min={1}
            max={2000}
            onChange={(e) => setMax(Number(e.target.value))}
            style={{ width: 90 }}
            title="Max businesses to score per job"
          />
          <label className="check">
            <input type="checkbox" checked={explain} onChange={(e) => setExplain(e.target.checked)} />
            explain with GLM
          </label>
          <button
            className="btn"
            disabled={scoreMutation.isPending}
            onClick={() => scoreMutation.mutate()}
          >
            {scoreMutation.isPending ? "Queuing…" : "Score all"}
          </button>
        </div>
      </div>

      {scoreMutation.isSuccess && (
        <div className="notice">
          Scoring job #{scoreMutation.data.id} queued. Scores are computed with a rules engine;
          {explain ? " GLM will write a short explanation per lead." : " no AI explanations."}
        </div>
      )}

      <div className="toolbar">
        <input
          placeholder="Search name / category…"
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
          value={filters.min_score ?? ""}
          onChange={(e) => patch({ min_score: e.target.value ? Number(e.target.value) : undefined })}
        >
          <option value="">any score</option>
          <option value="40">40+</option>
          <option value="60">60+</option>
          <option value="70">70+</option>
          <option value="85">85+</option>
        </select>
        <select
          value={filters.has_llm === undefined ? "" : filters.has_llm ? "yes" : "no"}
          onChange={(e) =>
            patch({ has_llm: e.target.value === "yes" ? true : e.target.value === "no" ? false : undefined })
          }
        >
          <option value="">AI: any</option>
          <option value="yes">AI: explained</option>
          <option value="no">AI: none</option>
        </select>
        <span className="count">{isFetching ? "…" : `${total} scored`}</span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((h) => (
                  <th key={h.id}>{flexRender(h.column.columnDef.header, h.getContext())}</th>
                ))}
                <th style={{ width: 40 }} />
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} onClick={() => setSelected(row.original)}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                ))}
                <td>
                  <button className="dots-btn" title="Details">
                    ⋯
                  </button>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !isFetching && (
              <tr>
                <td colSpan={columns.length + 1} className="muted">
                  No scores yet. Click <strong>Score all</strong> to rank your leads.
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

      {selected && <ScoreDrawer lead={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function ScoreDrawer({ lead, onClose }: { lead: ScoredLead; onClose: () => void }) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <h2>{lead.name}</h2>
        <span className={`score-chip big ${scoreClass(lead.score)}`}>
          {lead.score ?? "—"}
          <small>/100</small>
        </span>
        {lead.main_category && <span className="badge">{lead.main_category}</span>}
        <dl>
          <dt>Factors</dt>
          {lead.factors && lead.factors.length > 0 ? (
            <dd>
              <div className="factor-list">
                {lead.factors.map((f) => (
                  <div className="factor" key={f.name}>
                    <div className="factor-head">
                      <span>{f.name}</span>
                      <span className="muted">
                        {f.contribution}/{f.weight}
                      </span>
                    </div>
                    <div className="factor-bar">
                      <div
                        className="factor-fill"
                        style={{ width: `${(f.contribution / f.weight) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </dd>
          ) : (
            <dd className="muted">No factor breakdown.</dd>
          )}
          <dt>AI explanation</dt>
          <dd>
            {lead.llm_summary ? lead.llm_summary : <span className="muted">No AI summary (score without explain).</span>}
          </dd>
          <dt>City</dt>
          <dd>{lead.city ?? <span className="muted">—</span>}</dd>
          <dt>Rating</dt>
          <dd>
            {lead.rating != null
              ? `${lead.rating} (${lead.reviews_count ?? 0} reviews)`
              : <span className="muted">—</span>}
          </dd>
          <dt>Scored at</dt>
          <dd>
            {lead.scored_at ? new Date(lead.scored_at).toLocaleString() : <span className="muted">—</span>}
          </dd>
        </dl>
        <button className="btn secondary" onClick={onClose} style={{ marginTop: 18 }}>
          Close
        </button>
      </div>
    </div>
  );
}
