import {
  DashboardIcon,
  EnrichIcon,
  ExportIcon,
  JobsIcon,
  ScoreIcon,
  SettingsIcon,
  StarIcon,
} from "./icons.tsx";

export type Page =
  | "leads"
  | "jobs"
  | "enrichment"
  | "scoring"
  | "export"
  | "settings";

const NAV: { section: string; items: { label: string; page: Page; icon: React.ReactNode }[] }[] = [
  {
    section: "Workspace",
    items: [
      { label: "Dashboard", page: "leads", icon: <DashboardIcon /> },
      { label: "Jobs", page: "jobs", icon: <JobsIcon /> },
    ],
  },
  {
    section: "Pipeline",
    items: [
      { label: "Enrichment", page: "enrichment", icon: <EnrichIcon /> },
      { label: "Scoring", page: "scoring", icon: <ScoreIcon /> },
      { label: "Export", page: "export", icon: <ExportIcon /> },
      { label: "Settings", page: "settings", icon: <SettingsIcon /> },
    ],
  },
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

      {NAV.map((group) => (
        <div key={group.section}>
          <div className="nav-section-label">{group.section}</div>
          {group.items.map((item) => (
            <button
              key={item.page}
              className={`nav-pill ${page === item.page ? "active" : ""}`}
              onClick={() => onNavigate(item.page)}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      ))}

      <div className="spacer" />
    </aside>
  );
}
