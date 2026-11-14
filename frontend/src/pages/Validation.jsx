// Step 8 of the PS: PK, FK, enums, date order, reconciliation, lifecycle and duplicate checks.
import { api } from "../api/safetyApi";
import { StatusBadge } from "../components/common/Badges";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { fmtNum } from "../utils/formatters";

export default function Validation() {
  const state = useFetch(api.validation);
  const counts = useFetch(api.dbCounts);
  return (
    <Async state={state}>
      {(v) => {
        const cats = [...new Set(v.checks.map((c) => c.category))];
        return (
          <>
            <PageHead title="Validation Summary" subtitle="python -m scripts.validate · EXPECTED = violations are exactly the labelled, injected edge cases" />
            <div className="grid g4">
              <KpiCard label="Overall" value={<StatusBadge value={v.overall} />} sub={`${v.total_checks} checks`} tone="ok" />
              <KpiCard label="Passed" value={v.passed} tone="ok" />
              <KpiCard label="Expected anomalies" value={v.expected_anomalies} sub="labelled edge cases found" tone="warn" />
              <KpiCard label="Failed" value={v.failed} tone={v.failed ? "bad" : "ok"} />
            </div>
            <div className="grid g2">
              <Card title="Checks by category">
                {cats.map((cat) => (
                  <details key={cat} open={cat !== "enum" && cat !== "foreign_key" && cat !== "primary_key"}>
                    <summary>{cat.replace("_", " ")} ({v.checks.filter((c) => c.category === cat).length})</summary>
                    <DataTable rows={v.checks.filter((c) => c.category === cat)} columns={[
                      { key: "status", label: "Status", render: (s) => <StatusBadge value={s} /> },
                      { key: "check", label: "Check" },
                      { key: "violations", label: "Violations", num: true },
                      { key: "expected_issue", label: "Labelled issue", render: (s, r) => (s ? `${s} (${r.labelled})` : "-") },
                    ]} />
                  </details>
                ))}
              </Card>
              <Card title="Row counts - live in MySQL (Tier 3)" hint="Read directly from safety_db via /api/meta/db-counts">
                <Async state={counts}>
                  {(c) => (
                    <DataTable rows={Object.entries(c).map(([table, rows]) => ({ table, rows, file: v.row_counts[table] }))} columns={[
                      { key: "table", label: "Table", render: (t) => <span className="mono">{t}</span> },
                      { key: "rows", label: "MySQL rows", num: true, render: fmtNum },
                      { key: "file", label: "CSV rows", num: true, render: (f) => (f === undefined ? "separate file" : fmtNum(f)) },
                    ]} />
                  )}
                </Async>
              </Card>
            </div>
          </>
        );
      }}
    </Async>
  );
}