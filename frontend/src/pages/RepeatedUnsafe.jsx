// The core business answer: machines where the same unsafe condition repeats (>= 3 in 7 days).
import { Link } from "react-router-dom";
import { api } from "../api/safetyApi";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import { SimpleBarChart } from "../components/charts/Charts";
import useFetch from "../hooks/useFetch";
import { fmtTs } from "../utils/formatters";

export default function RepeatedUnsafe() {
  const state = useFetch(api.repeatedUnsafe);
  return (
    <Async state={state}>
      {(d) => (
        <>
          <PageHead title="Repeated Unsafe Conditions" subtitle={`Rule: ${d.rule}. Risk = count in window × zone hazard × 2 for bypass cases.`} />
          <div className="grid g3">
            <KpiCard label="Repeated unsafe conditions" value={d.conditions} sub="machine + rule combinations" tone="bad" />
            <KpiCard label="Machines affected" value={d.machines_affected} tone="warn" />
            <KpiCard label="Highest risk" value={d.items[0]?.machine_id || "-"} sub={d.items[0]?.rule_code} tone="bad" />
          </div>
          <Card title="Escalation list (highest risk first)">
            <DataTable rows={d.items} columns={[
              { key: "risk_score", label: "Risk", num: true, render: (v) => <b>{v}</b> },
              { key: "machine_id", label: "Machine", render: (v, r) => <>{r.machine_name} <span className="mono">({v})</span></> },
              { key: "plant_id", label: "Plant" },
              { key: "zone_name", label: "Zone", render: (v, r) => `${v} (hazard ${r.hazard_level})` },
              { key: "rule_code", label: "Rule", render: (v, r) => <span title={r.rule_description}>{v}</span> },
              { key: "max_count_in_window", label: "In 7 days", num: true },
              { key: "total_count", label: "Total", num: true },
              { key: "open_incidents", label: "Open inc.", num: true },
              { key: "open_actions", label: "Open actions", num: true },
              { key: "last_incident_ts", label: "Last", render: fmtTs },
              { key: "incidents", label: "Incidents in window", render: (v) => v.map((i) => (
                <Link key={i.incident_id} to={`/incidents/${i.incident_id}`} className="mono" style={{ display: "block" }}>{i.incident_id}</Link>)) },
            ]} />
          </Card>
          <div style={{ height: 14 }} />
          <Card title="Incidents per machine (rule-based)">
            <SimpleBarChart data={d.incidents_per_machine} x="machine_id" y="incidents" color="#dc2626" />
          </Card>
        </>
      )}
    </Async>
  );
}