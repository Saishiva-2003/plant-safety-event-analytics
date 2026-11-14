// Incident traceability: machine states, interlocks, alarms, acks and corrective actions on one timeline.
import { Link, useParams } from "react-router-dom";
import { api } from "../api/safetyApi";
import { SeverityBadge, StatusBadge } from "../components/common/Badges";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { TYPE_COLORS, fmtTs } from "../utils/formatters";

export default function IncidentTrace() {
  const { id } = useParams();
  const state = useFetch(() => api.trace(id), [id]);
  return (
    <Async state={state}>
      {(d) => {
        const i = d.incident;
        return (
          <>
            <PageHead title={`Incident ${i.incident_id}`}
                      subtitle={`${i.description} · ${i.machine_name} (${i.machine_id}) · ${i.zone_name}`}
                      right={<Link to="/incidents">← all incidents</Link>} />
            <div className="grid g6">
              <KpiCard label="Rule" value={i.rule_code.split("_")[0]} sub={i.rule_code} tone="bad" />
              <KpiCard label="Severity" value={<SeverityBadge value={i.severity} />} sub={`opened ${fmtTs(i.opened_ts)}`} />
              <KpiCard label="Status" value={<StatusBadge value={i.status} />} sub={i.closed_ts ? `closed ${fmtTs(i.closed_ts)}` : "not closed"} />
              <KpiCard label="Machine state" value={d.machine_state_at_open} sub="at incident open" tone="warn" />
              <KpiCard label="Linked alarms" value={d.linked_alarms} sub={`${d.state_events} state / ${d.interlock_events} interlock events`} />
              <KpiCard label="Traceable" value={<StatusBadge value={d.traceable ? "YES" : "NO"} />} sub={`${d.actions.length} corrective actions`} tone={d.traceable ? "ok" : "bad"} />
            </div>
            {d.flags.length > 0 && (
              <div className="error-box"><b>Data-quality flags:</b> {d.flags.join(" · ")}</div>
            )}
            <div className="grid g2">
              <Card title="Traceability timeline" hint={`${fmtTs(d.window_start)} → ${fmtTs(d.window_end)} plus corrective-action history`}>
                <div className="timeline">
                  {d.timeline.map((e, k) => (
                    <div key={k} className={`tl-item ${e.flag ? "flagged" : ""}`}>
                      <span className="dot" style={{ background: TYPE_COLORS[e.type] }} />
                      <div className="when">{fmtTs(e.ts)} · <b style={{ color: TYPE_COLORS[e.type] }}>{e.type}</b></div>
                      <div className="title">{e.title} {e.flag && <span className="badge pill-bad">{e.flag}</span>}</div>
                      <div className="detail">{e.detail}</div>
                    </div>
                  ))}
                </div>
              </Card>
              <Card title="Corrective actions" hint="Lifecycle: OPEN → IN_PROGRESS → PENDING_VERIFICATION → VERIFIED → CLOSED">
                <DataTable rowKey="action_id" rows={d.actions} empty="No corrective actions yet" columns={[
                  { key: "action_id", label: "Action", render: (v) => <span className="mono">{v}</span> },
                  { key: "action_type", label: "Type" },
                  { key: "description", label: "Description" },
                  { key: "status", label: "Status", render: (v) => <StatusBadge value={v} /> },
                  { key: "due_ts", label: "Due", render: fmtTs },
                  { key: "verified_by", label: "Verified by", render: (v, r) => v || (r.status === "CLOSED" ? <span className="badge pill-bad">missing</span> : "-") },
                ]} />
              </Card>
            </div>
          </>
        );
      }}
    </Async>
  );
}