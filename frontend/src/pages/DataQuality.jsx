// The 5 labelled edge cases: what the detectors found (no ground truth) + score against ground truth.
import { api } from "../api/safetyApi";
import { ScoreBadge } from "../components/common/Badges";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { fmtTs } from "../utils/formatters";

export default function DataQuality() {
  const evaluation = useFetch(api.evaluation);
  const anomalies = useFetch(api.anomalies);
  return (
    <>
      <PageHead title="Data Quality & Detector Evaluation"
                subtitle="Detectors run on operational data only; ground_truth.csv is used solely to score them (precision / recall / F1)." />
      <Async state={evaluation}>
        {(e) => (
          <>
            <div className="grid g3">
              <KpiCard label="Macro F1 - 5 edge cases" value={e.macro_f1_anomalies.toFixed(3)} sub="ack before alarm, impossible interlock, no trigger, replay, unverified closure" tone="ok" />
              <KpiCard label="Macro F1 - all 8 checks" value={e.macro_f1_all.toFixed(3)} sub="incl. floods, nuisance, repeated unsafe" tone="ok" />
              <KpiCard label="Ground-truth policy" value="Separate" sub={e.note} />
            </div>
            <Card title="Evaluation against ground truth">
              <DataTable rowKey="issue_type" rows={e.items} columns={[
                { key: "issue_type", label: "Issue / pattern", render: (v) => <span className="mono">{v}</span> },
                { key: "category", label: "Type" },
                { key: "labelled", label: "Labelled", num: true },
                { key: "detected", label: "Detected", num: true },
                { key: "tp", label: "TP", num: true }, { key: "fp", label: "FP", num: true }, { key: "fn", label: "FN", num: true },
                { key: "precision", label: "Precision", render: (v) => <ScoreBadge value={v} /> },
                { key: "recall", label: "Recall", render: (v) => <ScoreBadge value={v} /> },
                { key: "f1", label: "F1", render: (v) => <ScoreBadge value={v} /> },
              ]} />
            </Card>
          </>
        )}
      </Async>
      <div style={{ height: 14 }} />
      <Async state={anomalies}>
        {(a) => (
          <Card title={`Detected anomalies (${a.total_detected})`} hint="Each issue with the decision the business rule expects">
            {a.issues.map((i) => (
              <details key={i.issue_type} style={{ borderTop: "1px solid #e3e8ee", padding: "4px 0" }}>
                <summary>
                  {i.issue_type} - <span style={{ fontWeight: 400 }}>{i.description}</span>{" "}
                  <span className="badge pill-warn">{i.detected}</span>{" "}
                  <span className="badge pill-info">{i.expected_decision}</span>
                </summary>
                <div style={{ maxHeight: 260, overflowY: "auto" }}>
                  <DataTable rows={i.items.slice(0, 100)} columns={[
                    { key: "record_id", label: `${i.record_type} ID`, render: (v) => <span className="mono">{v}</span> },
                    { key: "related_id", label: "Related", render: (v) => <span className="mono">{v || "-"}</span> },
                    { key: "machine_id", label: "Machine" },
                    { key: "event_ts", label: "Time", render: fmtTs },
                    { key: "detail", label: "Detail" },
                  ]} />
                </div>
              </details>
            ))}
          </Card>
        )}
      </Async>
    </>
  );
}