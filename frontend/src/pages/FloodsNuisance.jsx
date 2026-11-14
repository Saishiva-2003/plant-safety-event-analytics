// Alarm floods (> 10 alarms / 10 min / plant) and nuisance clusters (chattering / fleeting bad actors).
import { api } from "../api/safetyApi";
import { SeverityBadge, StatusBadge } from "../components/common/Badges";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import { SimpleBarChart } from "../components/charts/Charts";
import useFetch from "../hooks/useFetch";
import { fmtDuration, fmtNum, fmtPct, fmtTs } from "../utils/formatters";

export default function FloodsNuisance() {
  const floods = useFetch(api.floods);
  const nuisance = useFetch(() => api.nuisance(40));
  return (
    <>
      <PageHead title="Alarm Floods & Nuisance Alarms" subtitle="ISA-18.2 style alarm-management analysis" />
      <Async state={floods}>
        {(f) => (
          <>
            <div className="grid g4">
              <KpiCard label="Flood episodes" value={f.episodes} sub={f.rule} tone="warn" />
              <KpiCard label="Alarms in floods" value={fmtNum(f.flood_alarms)} sub={`${fmtPct(f.share_of_alarms_pct)} of all alarms`} tone="warn" />
              <KpiCard label="Largest flood" value={fmtNum(f.largest)} sub="alarms in one episode" tone="bad" />
              <KpiCard label="Floods per plant" value={Object.entries(f.per_plant).map(([k, v]) => `${k}:${v}`).join("  ")} />
            </div>
            <Card title="Flood episodes" hint="Replay duplicates and chattering alarms are excluded before counting">
              <div style={{ maxHeight: 360, overflowY: "auto" }}>
                <DataTable rowKey="flood_id" rows={f.items} columns={[
                  { key: "flood_id", label: "Flood", render: (v) => <span className="mono">{v}</span> },
                  { key: "plant_id", label: "Plant" },
                  { key: "start_ts", label: "Start", render: fmtTs },
                  { key: "duration_sec", label: "Duration", num: true, render: fmtDuration },
                  { key: "alarm_count", label: "Alarms", num: true },
                  { key: "machines_involved", label: "Machines", num: true },
                  { key: "top_machine_id", label: "Top machine", render: (v) => <span className="mono">{v}</span> },
                  { key: "unacked", label: "Unacked", num: true },
                  { key: "delayed", label: "Delayed", num: true },
                ]} />
              </div>
            </Card>
          </>
        )}
      </Async>
      <div style={{ height: 14 }} />
      <Async state={nuisance}>
        {(n) => (
          <>
            <div className="grid g3">
              <KpiCard label="Nuisance alarms (bad actors)" value={n.nuisance_pairs} sub="machine + alarm pairs" tone="warn" />
              <KpiCard label="Alarms from nuisance" value={fmtNum(n.alarms_from_nuisance)} sub={`${fmtPct(n.share_of_alarms_pct)} of all alarms`} tone="warn" />
              <KpiCard label="Chattering activations" value={fmtNum(n.chatter_alarms_total)} sub={n.rule} />
            </div>
            <div className="grid g2">
              <Card title="Top bad actors by chatter episodes">
                <SimpleBarChart horizontal height={320}
                  data={n.items.filter((p) => p.is_nuisance).slice(0, 12).map((p) => ({ name: `${p.machine_id} ${p.alarm_code.split("-").slice(1).join("-")}`, episodes: p.chatter_episodes }))}
                  x="name" y="episodes" color="#ea580c" />
              </Card>
              <Card title="Nuisance cluster details">
                <div style={{ maxHeight: 340, overflowY: "auto" }}>
                  <DataTable rows={n.items.slice(0, 30)} columns={[
                    { key: "machine_id", label: "Machine", render: (v) => <span className="mono">{v}</span> },
                    { key: "alarm_code", label: "Alarm", render: (v) => <span className="mono">{v}</span> },
                    { key: "severity", label: "Sev", render: (v) => <SeverityBadge value={v} /> },
                    { key: "total_alarms", label: "Total", num: true },
                    { key: "chatter_episodes", label: "Episodes", num: true },
                    { key: "fleeting_pct", label: "Fleeting", num: true, render: fmtPct },
                    { key: "unacked_pct", label: "Unacked", num: true, render: fmtPct },
                    { key: "is_nuisance", label: "Nuisance", render: (v) => <StatusBadge value={v ? "YES" : "ENGAGED"} /> },
                  ]} />
                </div>
              </Card>
            </div>
          </>
        )}
      </Async>
    </>
  );
}