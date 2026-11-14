// Left navigation: one link per page, grouped by purpose, plus live backend/DB health.
import { NavLink } from "react-router-dom";
import { api } from "../../api/safetyApi";
import useFetch from "../../hooks/useFetch";
import { fmtNum } from "../../utils/formatters";

const GROUPS = [
  { title: "Start here", links: [["/checklist", "PS Checklist"]] },
  {
    title: "Safety analytics",
    links: [
      ["/", "Overview"],
      ["/alarms", "Alarm Explorer"],
      ["/floods", "Floods & Nuisance"],
      ["/incidents", "Incidents & Trace"],
      ["/unsafe", "Repeated Unsafe"],
    ],
  },
  {
    title: "Data quality & proof",
    links: [
      ["/quality", "Data Quality"],
      ["/validation", "Validation"],
      ["/reproducibility", "Reproducibility"],
    ],
  },
  { title: "Documentation", links: [["/model", "Data Model"], ["/rules", "Business Rules"]] },
];

export default function Sidebar() {
  const { data: health, error } = useFetch(api.health);
  return (
    <aside className="sidebar">
      <div className="logo">Plant Safety Analytics</div>
      <div className="tagline">Repeated unsafe conditions from alarms, states, acks &amp; actions</div>
      {GROUPS.map((g) => (
        <div key={g.title}>
          <div className="group">{g.title}</div>
          {g.links.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              {label}
            </NavLink>
          ))}
        </div>
      ))}
      <div className="health">
        {error ? (
          <span style={{ color: "#ffb4ab" }}>Backend offline</span>
        ) : health ? (
          <>
            API <b style={{ color: "#a5d6a7" }}>OK</b> · MySQL {health.mysql_version.split("-")[0]}
            <br />
            {fmtNum(health.alarm_events)} alarm events in {health.database}
          </>
        ) : (
          "Connecting..."
        )}
      </div>
    </aside>
  );
}