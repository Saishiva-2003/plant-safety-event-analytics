// Documented business rules (generator/rules.py) - the same rules create the data and analyse it.
import { api } from "../api/safetyApi";
import { SeverityBadge } from "../components/common/Badges";
import { Card, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { fmtDuration, fmtNum } from "../utils/formatters";

const transitions = (obj) => Object.entries(obj).map(([from, to]) => ({ from, to: to.join(", ") }));

export default function Rules() {
  const state = useFetch(api.rules);
  return (
    <Async state={state}>
      {(r) => (
        <>
          <PageHead title="Business Rules" subtitle="Single source of truth: backend/generator/rules.py - used by the generator AND the analytics services" />
          <div className="grid g2">
            <Card title="Severity, weight and acknowledgement SLA">
              <DataTable rowKey="severity" rows={r.severity} columns={[
                { key: "severity", label: "Severity", render: (v) => <SeverityBadge value={v} /> },
                { key: "weight", label: "Priority weight", num: true },
                { key: "ack_sla_sec", label: "Ack SLA", num: true, render: fmtDuration },
              ]} />
              <p><b>Priority:</b> <code>{r.priority_formula}</code></p>
              <p><b>Interlock factor:</b> {Object.entries(r.interlock_factor).map(([k, v]) => `${k} ×${v}`).join(" · ")}</p>
            </Card>
            <Card title="Incident rules (incidents are derived, never random)">
              <DataTable rowKey="rule_code" rows={r.incident_rules} columns={[
                { key: "rule_code", label: "Rule", render: (v) => <span className="mono">{v}</span> },
                { key: "description", label: "Condition" },
                { key: "severity", label: "Severity" },
              ]} />
              <p><b>Repeated unsafe condition:</b> same machine + same rule ≥ {r.repeated_unsafe.min_count} times within {r.repeated_unsafe.window_days} days</p>
            </Card>
          </div>
          <div className="grid g3">
            <Card title="Alarm flood"><p>{r.flood.text}</p></Card>
            <Card title="Nuisance / chattering">
              <p>≥ {r.nuisance.chatter_min_count} activations within {r.nuisance.chatter_window_sec} s = chatter episode</p>
              <p>≥ {r.nuisance.nuisance_min_episodes} episodes = nuisance alarm · cleared ≤ {r.nuisance.fleeting_max_sec} s = fleeting</p>
            </Card>
            <Card title="Shifts">{Object.entries(r.shifts).map(([k, v]) => <p key={k}><b>{k}</b> {v}</p>)}</Card>
          </div>
          <div className="grid g3">
            <Card title="Machine state machine">
              <DataTable rows={transitions(r.machine_transitions)} columns={[{ key: "from", label: "From" }, { key: "to", label: "Allowed next" }]} />
            </Card>
            <Card title="Interlock state machine">
              <DataTable rows={transitions(r.interlock_transitions)} columns={[{ key: "from", label: "From" }, { key: "to", label: "Allowed next" }]} />
              <h3 style={{ marginTop: 12 }}>Lifecycles</h3>
              <p><b>Incident:</b> {r.incident_statuses.join(" → ")}</p>
              <p><b>Action:</b> {r.action_statuses.join(" → ")}</p>
            </Card>
            <Card title="Expected decisions per issue">
              <DataTable rows={Object.entries(r.expected_decisions).map(([issue, decision]) => ({ issue, decision }))} columns={[
                { key: "issue", label: "Issue", render: (v) => <span className="mono">{v}</span> },
                { key: "decision", label: "Decision", render: (v) => <span className="mono">{v}</span> },
              ]} />
            </Card>
          </div>
          <Card title="Generator">
            <p><b>Seed:</b> {r.generator.seed} · <b>Command:</b> <code>{r.generator.command}</code></p>
            <DataTable rows={Object.entries(r.generator.scales).map(([scale, v]) => ({ scale, ...v }))} columns={[
              { key: "scale", label: "Scale" },
              { key: "plants", label: "Plants", num: true }, { key: "machines", label: "Machines", num: true },
              { key: "alarm_definitions", label: "Alarm defs", num: true },
              { key: "alarm_events", label: "Alarm events", num: true, render: fmtNum }, { key: "days", label: "Days", num: true },
            ]} />
          </Card>
        </>
      )}
    </Async>
  );
}