// Colour-coded badges for severity, statuses and pass/fail results.
import { SEVERITY_COLORS } from "../../utils/formatters";

export function SeverityBadge({ value }) {
  return (
    <span className="badge" style={{ background: SEVERITY_COLORS[value] || "#90a4ae" }}>
      {value}
    </span>
  );
}

const STATUS_CLASS = {
  PASS: "pill-ok", DONE: "pill-ok", ON_TIME: "pill-ok", CLOSED: "pill-ok", VERIFIED: "pill-ok", ENGAGED: "pill-ok",
  YES: "pill-ok", EXPECTED: "pill-warn", DELAYED: "pill-warn", ACTION_PENDING: "pill-warn", INVESTIGATING: "pill-warn",
  PENDING_VERIFICATION: "pill-warn", IN_PROGRESS: "pill-info", OPEN: "pill-info", TRIPPED: "pill-warn",
  FAIL: "pill-bad", CHECK: "pill-bad", UNACKED: "pill-bad", INVALID: "pill-bad", BYPASSED: "pill-bad", NO: "pill-bad",
};

export function StatusBadge({ value }) {
  return <span className={`badge ${STATUS_CLASS[value] || "soft"}`}>{String(value).replaceAll("_", " ")}</span>;
}

export function ScoreBadge({ value }) {
  const cls = value >= 0.999 ? "pill-ok" : value >= 0.9 ? "pill-warn" : "pill-bad";
  return <span className={`badge ${cls}`}>{Number(value).toFixed(3)}</span>;
}