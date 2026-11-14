// Step 10 of the PS: generate twice with the same seed -> identical row counts and SHA-256 checksums.
import { api } from "../api/safetyApi";
import { StatusBadge } from "../components/common/Badges";
import { Card, KpiCard, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";
import { fmtNum } from "../utils/formatters";

export default function Reproducibility() {
  const repro = useFetch(api.reproducibility);
  const manifest = useFetch(api.manifest);
  return (
    <>
      <PageHead title="Reproducibility & Provenance" subtitle="python -m scripts.reproducibility · same seed → byte-identical output" />
      <Async state={repro}>
        {(r) => (
          <>
            <div className="grid g4">
              <KpiCard label="Result" value={<StatusBadge value={r.identical ? "YES" : "NO"} />} sub="two runs identical" tone={r.identical ? "ok" : "bad"} />
              <KpiCard label="Seed" value={r.seed} sub={`scale: ${r.scale}`} />
              <KpiCard label="Matches published data" value={<StatusBadge value={r.matches_published_dataset ? "YES" : "NO"} />} sub="database/seed vs fresh run" tone="ok" />
              <KpiCard label="Combined SHA-256" value={<span className="mono" style={{ fontSize: 13 }}>{r.combined_sha256_run1.slice(0, 24)}…</span>} sub="run 1 = run 2" />
            </div>
            <Card title="Run 1 vs Run 2 - every table">
              <DataTable rowKey="table" rows={r.tables} columns={[
                { key: "table", label: "Table", render: (t) => <span className="mono">{t}</span> },
                { key: "rows_run1", label: "Rows run 1", num: true, render: fmtNum },
                { key: "rows_run2", label: "Rows run 2", num: true, render: fmtNum },
                { key: "sha256_run1", label: "SHA-256 run 1", render: (s) => <span className="mono">{s}</span> },
                { key: "sha256_run2", label: "SHA-256 run 2", render: (s) => <span className="mono">{s}</span> },
                { key: "identical", label: "Same", render: (s) => <StatusBadge value={s ? "YES" : "NO"} /> },
              ]} />
            </Card>
          </>
        )}
      </Async>
      <div style={{ height: 14 }} />
      <Async state={manifest}>
        {(m) => (
          <Card title="Source manifest">
            <div className="grid g2">
              <div>
                <p><b>Generator:</b> {m.generator} v{m.generator_version}</p>
                <p><b>Command:</b> <code>{m.command}</code></p>
                <p><b>Window:</b> {m.window_start} → {m.window_end}</p>
                <p><b>Provenance:</b> {m.provenance}</p>
                <p><b>Exports:</b> <code>database/seed/csv</code>, <code>database/seed/json</code>, <code>database/seed/sql/seed.sql</code>,
                  <code> database/ground_truth</code></p>
              </div>
              <div>
                <p><b>Ground truth:</b> {fmtNum(m.ground_truth.rows)} rows · <span className="mono">{m.ground_truth.csv_sha256.slice(0, 16)}…</span></p>
                <p><b>seed.sql SHA-256:</b> <span className="mono">{m.seed_sql_sha256.slice(0, 32)}…</span></p>
                <p><b>Combined SHA-256:</b> <span className="mono">{m.combined_sha256}</span></p>
              </div>
            </div>
          </Card>
        )}
      </Async>
    </>
  );
}