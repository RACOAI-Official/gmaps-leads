import {
  DashboardIcon,
  EnrichIcon,
  ExportIcon,
  JobsIcon,
  LockIcon,
  ScoreIcon,
  SettingsIcon,
  StarIcon,
} from "./icons.tsx";

export type Page = "leads" | "jobs";

const FUTURE: { label: string; icon: React.ReactNode }[] = [
  { label: "Enrichment", icon: <EnrichIcon /> },
  { label: "Scoring", icon: <ScoreIcon /> },
  { label: "Export", icon: <ExportIcon /> },
  { label: "Settings", icon: <SettingsIcon /> },
];

export function Sidebar({
  page,
  onNavigate,
}: {
  page: Page;
  onNavigate: (p: Page) => void;
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <StarIcon />
        <span>Leadstar</span>
      </div>

      <div className="nav-section-label">Workspace</div>
      <button
        className={`nav-pill ${page === "leads" ? "active" : ""}`}
        onClick={() => onNavigate("leads")}
      >
        <DashboardIcon />
        Dashboard
      </button>
      <button
        className={`nav-pill ${page === "jobs" ? "active" : ""}`}
        onClick={() => onNavigate("jobs")}
      >
        <JobsIcon />
        Jobs
      </button>

      <div className="nav-section-label">Pipeline</div>
      {FUTURE.map((item) => (
        <button
          key={item.label}
          className="nav-pill disabled"
          disabled
          title="Coming in a later phase"
        >
          {item.icon}
          {item.label}
          <LockIcon />
        </button>
      ))}

      <div className="spacer" />
    </aside>
  );
}
