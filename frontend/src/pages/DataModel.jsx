// Step 1 of the PS: entities, keys, cardinality, lifecycle states and the field-level data dictionary.
import { useState } from "react";
import { api } from "../api/safetyApi";
import { Card, PageHead } from "../components/common/Card";
import DataTable from "../components/common/DataTable";
import { Async } from "../components/common/Status";
import useFetch from "../hooks/useFetch";

export default function DataModel() {
  const state = useFetch(api.dataDictionary);
  const [table, setTable] = useState("alarm_event");
  return (
    <Async state={state}>
      {(d) => {
        const t = d.tables.find((x) => x.table === table) || d.tables[0];
        return (
          <>
            <PageHead title="Data Model & Data Dictionary" subtitle="Generated from database/schema/schema.sql - the single source of truth for Tier 3" />
            <div className="grid g2">
              <Card title={`Relationships & cardinality (${d.relationships.length})`}>
                <DataTable rows={d.relationships} columns={[
                  { key: "parent", label: "Parent", render: (v) => <span className="mono">{v}</span> },
                  { key: "cardinality", label: "Cardinality", render: (v) => <b>{v}</b> },
                  { key: "child", label: "Child", render: (v) => <span className="mono">{v}</span> },
                  { key: "via", label: "Via (FK / bridge)", render: (v) => <span className="mono">{v}</span> },
                ]} />
              </Card>
              <Card title="ID conventions">
                <DataTable rows={Object.entries(d.id_conventions).map(([entity, format]) => ({ entity, format }))} columns={[
                  { key: "entity", label: "Entity" },
                  { key: "format", label: "Format", render: (v) => <span className="mono">{v}</span> },
                ]} />
                <h3 style={{ marginTop: 14 }}>Entities</h3>
                <DataTable rows={d.tables} onRowClick={(r) => setTable(r.table)} columns={[
                  { key: "table", label: "Table", render: (v) => <a className="mono">{v}</a> },
                  { key: "kind", label: "Kind" },
                  { key: "primary_key", label: "PK", render: (v) => <span className="mono">{v.join(", ")}</span> },
                  { key: "lifecycle", label: "Lifecycle", render: (v) => v || "-" },
                ]} />
              </Card>
            </div>
            <Card title={`Data dictionary - ${t.table}`} hint={t.description}
                  right={<select value={t.table} onChange={(e) => setTable(e.target.value)}>
                    {d.tables.map((x) => <option key={x.table}>{x.table}</option>)}
                  </select>}>
              <DataTable rowKey="field" rows={t.fields} columns={[
                { key: "field", label: "Field", render: (v, r) => <span className="mono">{r.primary_key ? "🔑 " : ""}{v}</span> },
                { key: "type", label: "Type", render: (v) => <span className="mono">{v}</span> },
                { key: "required", label: "Required", render: (v) => (v ? "yes" : "optional") },
                { key: "allowed_values", label: "Allowed values", render: (v) => (v ? v.join(", ") : "-") },
                { key: "units", label: "Units", render: (v) => v || "-" },
                { key: "unique", label: "Unique", render: (v) => (v ? "yes" : "-") },
                { key: "foreign_key", label: "FK →", render: (v) => <span className="mono">{v || "-"}</span> },
                { key: "validation", label: "Validation rule" },
              ]} />
            </Card>
          </>
        );
      }}
    </Async>
  );
}