// Display helpers (dates, durations, numbers, colours).
export const fmtTs = (ts) => (ts ? String(ts).replace("T", " ").slice(0, 19) : "-");
export const fmtDate = (ts) => (ts ? String(ts).slice(0, 10) : "-");
export const fmtNum = (n) => (n === null || n === undefined ? "-" : Number(n).toLocaleString("en-IN"));
export const fmtPct = (n) => (n === null || n === undefined ? "-" : `${Number(n).toFixed(1)}%`);

export function fmtDuration(sec) {
  if (sec === null || sec === undefined) return "-";
  const s = Math.abs(Number(sec));
  const sign = Number(sec) < 0 ? "-" : "";
  if (s < 60) return `${sign}${s.toFixed(0)}s`;
  if (s < 3600) return `${sign}${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  return `${sign}${Math.floor(s / 3600)}h ${Math.round((s % 3600) / 60)}m`;
}

// Colour only signals abnormal priority; normal data stays grey
export const SEVERITY_COLORS = { CRITICAL: "#dc2626", HIGH: "#ea580c", MEDIUM: "#eab308", LOW: "#64748b" };
export const TYPE_COLORS = {
  STATE: "#64748b", INTERLOCK: "#7c3aed", ALARM: "#dc2626", ACK: "#16a34a", INCIDENT: "#be123c", ACTION: "#2563eb",
};
export const NEUTRAL = "#94a3b8";