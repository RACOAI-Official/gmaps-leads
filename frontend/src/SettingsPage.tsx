import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  fetchQueueHealth,
  fetchSettings,
  llmTest,
  patchScrapeKnobs,
  rescoreAll,
  retryFailed,
  type SettingsData,
} from "./api.ts";

export function SettingsPage() {
  const qc = useQueryClient();
  const { data: settings } = useQuery({ queryKey: ["settings"], queryFn: fetchSettings });
  const { data: queue } = useQuery({ queryKey: ["queue"], queryFn: fetchQueueHealth });

  if (!settings) {
    return (
      <div className="panel">
        <div className="panel-head">
          <h3>Settings</h3>
        </div>
        <div className="toolbar muted">Loading…</div>
      </div>
    );
  }

  return (
    <div className="settings-stack">
      <ConfigSection settings={settings} />
      <ScrapeKnobsSection settings={settings} qc={qc} />
      <LLMConsoleSection />
      <DataManagementSection queue={queue?.breakdown ?? {}} qc={qc} />
    </div>
  );
}

function ConfigSection({ settings }: { settings: SettingsData }) {
  const c = settings.counts;
  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Runtime config</h3>
      </div>
      <div className="kv-grid">
        <KV label="Database" value={<code>{settings.database_url}</code>} />
        <KV label="LLM format" value={<code>{settings.llm.format}</code>} />
        <KV label="LLM base URL" value={<code>{settings.llm.base_url || "—"}</code>} />
        <KV label="LLM model" value={<code>{settings.llm.model || "—"}</code>} />
        <KV
          label="LLM API key"
          value={
            settings.llm.api_key_present ? (
              <code>{settings.llm.api_key_masked}</code>
            ) : (
              <span className="muted">not set</span>
            )
          }
        />
        <KV
          label="LLM status"
          value={
            settings.llm.configured ? (
              <span className="status-done">configured</span>
            ) : (
              <span className="status-failed">not configured</span>
            )
          }
        />
      </div>
      <div className="count-row">
        <Stat n={c.leads} label="leads" />
        <Stat n={c.with_website} label="with website" />
        <Stat n={c.enrichments} label="enriched" />
        <Stat n={c.scores} label="scored" />
        <Stat n={c.scores_with_llm} label="AI explained" />
      </div>
    </div>
  );
}

function ScrapeKnobsSection({
  settings,
  qc,
}: {
  settings: SettingsData;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const s = settings.scrape;
  const [minS, setMinS] = useState(String(s.delay_min_s));
  const [maxS, setMaxS] = useState(String(s.delay_max_s));
  const [cap, setCap] = useState(String(s.daily_cap));

  const mut = useMutation({
    mutationFn: () =>
      patchScrapeKnobs({
        delay_min_s: Number(minS),
        delay_max_s: Number(maxS),
        daily_cap: Number(cap),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Scrape knobs</h3>
        <div className="right">
          <button className="btn" disabled={mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
      {mut.isSuccess && <div className="notice">Saved — applies to the next job.</div>}
      <div className="kv-grid">
        <label className="field">
          <span>Min delay (s)</span>
          <input type="number" step="0.5" min={0} max={120} value={minS} onChange={(e) => setMinS(e.target.value)} />
        </label>
        <label className="field">
          <span>Max delay (s)</span>
          <input type="number" step="0.5" min={0} max={120} value={maxS} onChange={(e) => setMaxS(e.target.value)} />
        </label>
        <label className="field">
          <span>Daily cap</span>
          <input type="number" min={0} max={10000} value={cap} onChange={(e) => setCap(e.target.value)} />
        </label>
        <div className="field">
          <span>Cooldown (h)</span>
          <input type="number" value={s.cooldown_hours} disabled title="env-only — restart to change" />
        </div>
        <div className="field">
          <span>Headless</span>
          <input
            type="text"
            value={s.headless ? "true" : "false"}
            disabled
            title="env-only — restart to change"
          />
        </div>
      </div>
      <div className="muted toolbar" style={{ fontSize: 12 }}>
        Delays and daily cap are live (editable). Cooldown &amp; headless are env-only.
      </div>
    </div>
  );
}

function LLMConsoleSection() {
  const [prompt, setPrompt] = useState("Reply with the single word OK.");
  const [result, setResult] = useState<null | {
    ok: boolean;
    model?: string;
    latency_ms?: number;
    reply?: string;
    error?: string;
    format?: string;
  }>(null);

  const mut = useMutation({
    mutationFn: () => llmTest(prompt),
    onSuccess: setResult,
  });

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>LLM test console</h3>
        <div className="right">
          <button className="btn" disabled={mut.isPending} onClick={() => mut.mutate()}>
            {mut.isPending ? "Sending…" : "Send test"}
          </button>
        </div>
      </div>
      <div className="toolbar">
        <input
          style={{ minWidth: 400 }}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Prompt…"
        />
      </div>
      {result && (
        <div className="console-result">
          {result.ok ? (
            <>
              <div className="console-meta">
                <span className="status-done">OK</span>
                <span className="muted">
                  {result.model} · {result.latency_ms}ms · {result.format}
                </span>
              </div>
              <pre>{result.reply}</pre>
            </>
          ) : (
            <>
              <div className="console-meta">
                <span className="status-failed">FAILED</span>
                <span className="muted">{result.format}</span>
              </div>
              <pre className="err">{result.error}</pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function DataManagementSection({
  queue,
  qc,
}: {
  queue: Record<string, Record<string, number>>;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const retryMut = useMutation({
    mutationFn: retryFailed,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["queue"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
  const rescoreMut = useMutation({
    mutationFn: rescoreAll,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const types = Object.keys(queue).sort();
  const statuses = Array.from(
    new Set(types.flatMap((t) => Object.keys(queue[t]))),
  ).sort();

  return (
    <div className="panel">
      <div className="panel-head">
        <h3>Data &amp; jobs</h3>
        <div className="right">
          <button
            className="btn secondary"
            disabled={retryMut.isPending}
            onClick={() => retryMut.mutate()}
          >
            Retry failed
          </button>
          <button className="btn" disabled={rescoreMut.isPending} onClick={() => rescoreMut.mutate()}>
            Re-score all (with GLM)
          </button>
        </div>
      </div>
      {retryMut.isSuccess && (
        <div className="notice">Re-queued {retryMut.data.requeued} failed/blocked jobs.</div>
      )}
      {rescoreMut.isSuccess && (
        <div className="notice">
          Scoring job #{rescoreMut.data.job_id} queued for {rescoreMut.data.total_businesses} businesses.
        </div>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Job type</th>
              {statuses.map((st) => (
                <th key={st}>{st}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {types.map((t) => (
              <tr key={t}>
                <td>{t}</td>
                {statuses.map((st) => (
                  <td key={st}>{queue[t][st] ?? 0}</td>
                ))}
              </tr>
            ))}
            {types.length === 0 && (
              <tr>
                <td colSpan={statuses.length + 1} className="muted">
                  No jobs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="kv">
      <span className="kv-label">{label}</span>
      <span className="kv-value">{value}</span>
    </div>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <div className="stat">
      <strong>{n.toLocaleString()}</strong>
      <span className="muted">{label}</span>
    </div>
  );
}
