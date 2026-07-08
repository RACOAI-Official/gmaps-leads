import { useState } from "react";
import { LeadsPage } from "./LeadsPage.tsx";
import { JobsPage } from "./JobsPage.tsx";

type Tab = "leads" | "jobs";

export function App() {
  const [tab, setTab] = useState<Tab>("leads");
  return (
    <div className="app">
      <header className="topbar">
        <h1>gmaps-leads</h1>
        <nav>
          <button
            className={tab === "leads" ? "active" : ""}
            onClick={() => setTab("leads")}
          >
            Leads
          </button>
          <button
            className={tab === "jobs" ? "active" : ""}
            onClick={() => setTab("jobs")}
          >
            Jobs
          </button>
        </nav>
      </header>
      {tab === "leads" ? <LeadsPage /> : <JobsPage />}
    </div>
  );
}
