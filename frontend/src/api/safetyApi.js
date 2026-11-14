// One function per backend endpoint (pages never build URLs themselves).
import client from "./client";

const get = (url, params) => client.get(url, { params }).then((r) => r.data);

export const api = {
  health: () => get("/api/health"),
  kpis: () => get("/api/dashboard/kpis"),
  alarms: (params) => get("/api/alarms", params),
  floods: () => get("/api/analytics/floods"),
  nuisance: (limit = 50) => get("/api/analytics/nuisance", { limit }),
  repeatedUnsafe: () => get("/api/analytics/repeated-unsafe"),
  incidents: (params) => get("/api/incidents", params),
  trace: (id) => get(`/api/incidents/${id}/trace`),
  anomalies: () => get("/api/quality/anomalies"),
  evaluation: () => get("/api/quality/evaluation"),
  checklist: () => get("/api/meta/checklist"),
  validation: () => get("/api/meta/validation"),
  reproducibility: () => get("/api/meta/reproducibility"),
  manifest: () => get("/api/meta/manifest"),
  dataDictionary: () => get("/api/meta/data-dictionary"),
  rules: () => get("/api/meta/rules"),
  dbCounts: () => get("/api/meta/db-counts"),
  plants: () => get("/api/master/plants"),
  machines: (plant) => get("/api/master/machines", plant ? { plant } : undefined),
};