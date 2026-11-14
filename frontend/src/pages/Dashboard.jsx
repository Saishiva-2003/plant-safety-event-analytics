// Overview: dataset volumes, alarm trend, severity mix, acknowledgement performance, plants.
import { api } from "../api/safetyApi";
import { SeverityBadge } from "../components/common/Badges";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import { AlarmsPerDayChart, SimpleBarChart } from "../components/charts/Charts";
import useFetch from "../hooks/useFetch";
import { fmtDate, fmtDuration, fmtNum, fmtPct } from "../utils/formatters";

export default function Dashboard() {
  const state = useFetch(api.kpis);
  return (
    <Async state={state}>
      {(d) => {
        const t = d.totals, r = d.rates;
        return (
          <>
            <PageHead title="Safety Overview"
                      subtitle={`${fmtDate(d.window.start)} → ${fmtDate(d.window.end)} · ${t.plants} plants · ${t.machines} machines · ${t.alarm_definitions} alarm definitions`} />
            <div className="grid g6">
              <KpiCard label="Alarm events" value={fmtNum(t.alarm_events_raw)} sub={`${fmtNum(t.replay_duplicates_removed)} replay duplicates removed`} />
              <KpiCard label="Alarms / day" value={fmtNum(r.alarms_per_day)} sub={`${fmtNum(r.critical_alarms)} critical`} tone="bad" />
              <KpiCard label="Delayed acks" value={fmtPct(r.delayed_ack_pct)} sub={`MTTA ${fmtDuration(r.mtta_sec)}`} tone="warn" />
              <KpiCard label="Alarm floods" value={fmtNum(t.floods)} sub={`${t.nuisance_pairs} nuisance alarms`} tone="warn" />
              <KpiCard label="Incidents" value={fmtNum(t.incidents)} sub={`${t.open_incidents} open`} tone="bad" />
              <KpiCard label="State history" value={fmtNum(t.state_events)} sub={`${fmtNum(t.interlock_events)} interlock events`} tone="ok" />
            </div>
            <div className="grid g2">
              <Card title="Alarms per day by severity" hint="Unique alarms (replays excluded); spikes = alarm floods">
                <AlarmsPerDayChart data={d.alarms_per_day} />
              </Card>
              <Card title="Acknowledgement performance vs SLA" hint="Response time = ack_ts − raised_ts (derived)">
                <DataTable rowKey="severity" rows={d.ack_performance} columns={[
                  { key: "severity", label: "Severity", render: (v) => <SeverityBadge value={v} /> },
                  { key: "sla_sec", label: "SLA", num: true, render: fmtDuration },
                  { key: "alarms", label: "Alarms", num: true, render: fmtNum },
                  { key: "acked_pct", label: "Acked", num: true, render: fmtPct },
                  { key: "median_sec", label: "Median", num: true, render: fmtDuration },
                  { key: "delayed_pct", label: "Delayed", num: true, render: fmtPct },
                ]} />
                <h3 style={{ marginTop: 14 }}>Delayed acknowledgements by shift</h3>
                <DataTable rowKey="shift" rows={d.shift_performance} columns={[
                  { key: "shift", label: "Shift", render: (v) => ({ A: "A 06-14", B: "B 14-22", C: "C 22-06 (night)" }[v]) },
                  { key: "acked", label: "Acked", num: true, render: fmtNum },
                  { key: "delayed_pct", label: "Delayed", num: true, render: fmtPct },
                ]} />
              </Card>
            </div>
            <div className="grid g3">
              <Card title="Severity mix"><SimpleBarChart data={d.severity_mix} x="severity" y="count" /></Card>
              <Card title="Machine state when alarm raised"><SimpleBarChart data={d.machine_state_at_raise} x="state" y="count" /></Card>
              <Card title="Incidents by rule"><SimpleBarChart data={d.incident_rules} x="rule_code" y="count" color="#dc2626" horizontal height={220} /></Card>
            </div>
            <Card title="Plants">
              <DataTable rowKey="plant_id" rows={d.plants} columns={[
                { key: "plant_id", label: "Plant" },
                { key: "alarms", label: "Alarms", num: true, render: fmtNum },
                { key: "critical", label: "Critical", num: true },
                { key: "delayed", label: "Delayed acks", num: true, render: fmtNum },
                { key: "floods", label: "Floods", num: true },
                { key: "incidents", label: "Incidents", num: true },
              ]} />
            </Card>
          </>
        );
      }}
    </Async>
  );
}