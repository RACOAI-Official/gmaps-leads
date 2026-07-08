import type { Lead } from "./api.ts";

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>{value ?? <span className="muted">—</span>}</dd>
    </>
  );
}

export function LeadDrawer({ lead, onClose }: { lead: Lead; onClose: () => void }) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer" onClick={(e) => e.stopPropagation()}>
        <h2>{lead.name}</h2>
        {lead.main_category && <span className="badge">{lead.main_category}</span>}
        <dl>
          <Field label="Address" value={lead.address} />
          <Field label="City" value={lead.city} />
          <Field label="Phone" value={lead.phone} />
          <Field
            label="Website"
            value={
              lead.website ? (
                <a href={lead.website} target="_blank" rel="noreferrer">
                  {lead.website}
                </a>
              ) : null
            }
          />
          <Field
            label="Rating"
            value={
              lead.rating != null
                ? `${lead.rating} (${lead.reviews_count ?? 0} reviews)`
                : null
            }
          />
          <Field label="Source query" value={lead.source_query} />
          <Field
            label="Scraped at"
            value={lead.scraped_at ? new Date(lead.scraped_at).toLocaleString() : null}
          />
          <Field label="Place key" value={<code>{lead.place_key}</code>} />
        </dl>
        <button className="btn secondary" onClick={onClose} style={{ marginTop: 18 }}>
          Close
        </button>
      </div>
    </div>
  );
}
