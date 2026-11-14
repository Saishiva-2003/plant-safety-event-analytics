// Every requirement of the problem statement -> evidence -> live status (computed by the backend).
import { Link } from "react-router-dom";
import { api } from "../api/safetyApi";
import { StatusBadge } from "../components/common/Badges";
import { Card, PageHead } from "../components/common/Card";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";

export default function Checklist() {
  const state = useFetch(api.checklist);
  return (
    <>
      <PageHead title="Problem Statement Checklist"
                subtitle="Each requirement of the PS, the evidence produced, and where to see it - status is computed live from MySQL and the generated reports." />
      <div className="card" style={{ marginBottom: 14 }}>
        <h2>Three-tier architecture</h2>
        <div className="flow">
          <span className="step">React (Tier 1)</span><span className="arrow">→ REST/JSON →</span>
          <span className="step">FastAPI routes → services → repositories (Tier 2)</span><span className="arrow">→ SQLAlchemy →</span>
          <span className="step">MySQL safety_db (Tier 3)</span>
        </div>
        <div className="flow">
          <span className="step">generator (seed 20261022)</span><span className="arrow">→</span>
          <span className="step">CSV / JSON / SQL + ground_truth</span><span className="arrow">→</span>
          <span className="step">validator (80 checks)</span><span className="arrow">→</span>
          <span className="step">loader → MySQL</span><span className="arrow">→</span>
          <span className="step">detectors + evaluation</span>
        </div>
      </div>
      <Async state={state}>
        {(d) => (
          <Card title="Requirements" right={<span className="big-score">{d.done}/{d.total}</span>}>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th></th><th>Section</th><th>Requirement</th><th>Evidence</th><th>Status</th><th>See</th></tr>
                </thead>
                <tbody>
                  {d.items.map((i) => (
                    <tr key={i.requirement} className="check-row">
                      <td><span className={`lamp ${i.status === "DONE" ? "" : "off"}`} title={i.status} /></td>
                      <td><span className="section-tag">{i.section}</span></td>
                      <td>{i.requirement}</td>
                      <td style={{ color: "#3c4856" }}>{i.evidence}</td>
                      <td><StatusBadge value={i.status} /></td>
                      <td style={{ whiteSpace: "nowrap" }}><Link to={i.page}>View</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </Async>
    </>
  );
}