import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Sidebar, type Page } from "./Sidebar.tsx";
import { Topbar } from "./Topbar.tsx";
import { LeadsPage } from "./LeadsPage.tsx";
import { JobsPage } from "./JobsPage.tsx";
import { fetchLeads } from "./api.ts";

export function App() {
  const [page, setPage] = useState<Page>("leads");

  const { data: count } = useQuery({
    queryKey: ["leads-count"],
    queryFn: () => fetchLeads({ page_size: 1 }),
    select: (d) => d.total,
  });

  const topbar =
    page === "leads"
      ? {
          title: "Lead Dashboard",
          subtitle:
            count != null
              ? `${count.toLocaleString()} businesses scraped from Google Maps`
              : "Loading leads…",
        }
      : {
          title: "Scrape Jobs",
          subtitle: "Queue and monitor Google Maps scrape runs",
        };

  return (
    <div className="shell">
      <div className="card">
        <Sidebar page={page} onNavigate={setPage} />
        <main className="main">
          <Topbar title={topbar.title} subtitle={topbar.subtitle} />
          {page === "leads" ? <LeadsPage /> : <JobsPage />}
        </main>
      </div>
    </div>
  );
}
