// Incidents derived by rules R1-R3 (+ manual reports); click a row for the full trace.
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/safetyApi";
import { SeverityBadge, StatusBadge } from "../components/common/Badges";
import { Card, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { fmtTs } from "../utils/formatters";

const RULES = ["R1_BYPASS_CRITICAL", "R2_GUARD_TRIP_ESTOP", "R3_CRITICAL_UNACKED", "MANUAL_REPORT"];

export default function Incidents() {
  const nav = useNavigate();
  const [f, setF] = useState({ plant: "", rule: "", status: "" });
  const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
  const state = useFetch(() => api.incidents(params), [JSON.stringify(params)]);
  const sel = (k, opts) => (
    <label>{k}
      <select value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })}>
        <option value="">All</option>
        {opts.map((o) => <option key={o}>{o}</option>)}
      </select>
    </label>
  );
  return (
    <>
      <PageHead title="Incidents" subtitle="Created only by documented rules: R1 bypass + critical alarm while running · R2 guard trip → E-stop within 60 s · R3 critical alarm unacknowledged > 5 min" />
      <Card>
        <div className="filters">
          {sel("plant", ["P01", "P02", "P03", "P04"])}
          {sel("rule", RULES)}
          {sel("status", ["OPEN", "INVESTIGATING", "ACTION_PENDING", "CLOSED"])}
        </div>
        <Async state={state}>
          {(d) => (
            <>
              <div className="hint">{d.total} incidents - click a row to open its traceability timeline</div>
              <DataTable rowKey="incident_id" rows={d.items} onRowClick={(r) => nav(`/incidents/${r.incident_id}`)} columns={[
                { key: "incident_id", label: "Incident", render: (v) => <span className="mono">{v}</span> },
                { key: "opened_ts", label: "Opened", render: fmtTs },
                { key: "rule_code", label: "Rule" },
                { key: "severity", label: "Severity", render: (v) => <SeverityBadge value={v} /> },
                { key: "machine_name", label: "Machine", render: (v, r) => <>{v} <span className="mono">({r.machine_id})</span></> },
                { key: "zone_name", label: "Zone", render: (v, r) => `${v} (hazard ${r.hazard_level})` },
                { key: "status", label: "Status", render: (v) => <StatusBadge value={v} /> },
                { key: "actions_total", label: "Actions", num: true, render: (v, r) => `${r.actions_closed}/${v}` },
                { key: "traceable", label: "Traceable", render: (v) => <StatusBadge value={v ? "YES" : "NO"} /> },
              ]} />
            </>
          )}
        </Async>
      </Card>
    </>
  );
}