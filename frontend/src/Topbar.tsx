import { BellIcon, CalendarIcon, MoonIcon, SearchIcon } from "./icons.tsx";

export function Topbar({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <header className="topbar">
      <div className="greeting">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      <div className="pill-cluster">
        <button className="icon-btn" title="Search">
          <SearchIcon />
        </button>
        <button className="icon-btn" title="Theme">
          <MoonIcon />
        </button>
        <button className="icon-btn" title="Notifications">
          <BellIcon />
          <span className="dot" />
        </button>
        <button className="icon-btn" title="Calendar">
          <CalendarIcon />
        </button>
        <div className="avatar">🦊</div>
      </div>
    </header>
  );
}
