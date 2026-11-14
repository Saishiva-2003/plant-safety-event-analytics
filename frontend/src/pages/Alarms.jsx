// Alarm explorer: severe alarms first (priority score), filters, paging.
import { useState } from "react";
import { api } from "../api/safetyApi";
import { SeverityBadge, StatusBadge } from "../components/common/Badges";
import { Card, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { fmtDuration, fmtNum, fmtTs } from "../utils/formatters";

const EMPTY = { plant: "", severity: "", category: "", ack_status: "", flood_only: false, include_replays: false,
  search: "", sort: "priority" };

export default function Alarms() {
  const [f, setF] = useState(EMPTY);
  const [page, setPage] = useState(1);
  const params = Object.fromEntries(Object.entries({ ...f, page, size: 50 }).filter(([, v]) => v !== "" && v !== false));
  const state = useFetch(() => api.alarms(params), [JSON.stringify(params)]);
  const set = (k) => (e) => { setPage(1); setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }); };

  const sel = (k, label, opts) => (
    <label>{label}
      <select value={f[k]} onChange={set(k)}>
        <option value="">All</option>
        {opts.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );

  return (
    <>
      <PageHead title="Alarm Explorer"
                subtitle="Priority = severity weight × zone hazard × interlock factor (bypassed 2×, tripped 1.5×) + repeats in 24 h - severe alarms are listed first" />
      <Card>
        <div className="filters">
          {sel("plant", "Plant", ["P01", "P02", "P03", "P04"])}
          {sel("severity", "Severity", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])}
          {sel("category", "Category", ["SAFETY", "PROCESS", "EQUIPMENT", "SYSTEM"])}
          {sel("ack_status", "Ack status", ["ON_TIME", "DELAYED", "UNACKED", "INVALID"])}
          <label>Sort
            <select value={f.sort} onChange={set("sort")}>
              <option value="priority">Priority (severe first)</option>
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
            </select>
          </label>
          <label>Search<input value={f.search} onChange={set("search")} placeholder="ID / code / name" /></label>
          <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={f.flood_only} onChange={set("flood_only")} /> Floods only
          </label>
          <label style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={f.include_replays} onChange={set("include_replays")} /> Include replays
          </label>
          <button className="secondary" onClick={() => { setF(EMPTY); setPage(1); }}>Reset</button>
        </div>
        <Async state={state}>
          {(d) => (
            <>
              <DataTable rowKey="alarm_event_id" rows={d.items} columns={[
                { key: "priority_score", label: "Priority", num: true, render: (v) => <b>{v}</b> },
                { key: "severity", label: "Severity", render: (v) => <SeverityBadge value={v} /> },
                { key: "alarm_event_id", label: "Alarm ID", render: (v) => <span className="mono">{v}</span> },
                { key: "alarm_name", label: "Alarm", render: (v, r) => <>{v}<br /><span className="mono" style={{ color: "#6b7785" }}>{r.alarm_code}</span></> },
                { key: "machine_name", label: "Machine", render: (v, r) => <>{v}<br /><span className="mono">{r.machine_id}</span></> },
                { key: "raised_ts", label: "Raised", render: fmtTs },
                { key: "machine_state", label: "Machine state" },
                { key: "interlock_state_at_raise", label: "Interlocks", render: (v) => <StatusBadge value={v} /> },
                { key: "hazard_level", label: "Hazard", num: true },
                { key: "ack_status", label: "Ack", render: (v) => <StatusBadge value={v} /> },
                { key: "response_sec", label: "Response", num: true, render: fmtDuration },
                { key: "flood_id", label: "Flags", render: (v, r) => <>
                  {v && <span className="badge pill-warn">flood</span>} {r.chatter && <span className="badge pill-info">chatter</span>}{" "}
                  {r.is_replay && <span className="badge pill-bad">replay</span>}</> },
              ]} />
              <div className="pager">
                {fmtNum(d.total)} alarms · page {d.page} / {d.pages || 1}
                <button className="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
                <button className="secondary" disabled={page >= d.pages} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            </>
          )}
        </Async>
      </Card>
    </>
  );
}