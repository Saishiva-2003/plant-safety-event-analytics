// Axios instance for the FastAPI backend (Tier 2). Change VITE_API_URL in frontend/.env if needed.
import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

// Turn every backend error into one readable message: {"error": {"code", "message", "details"}}
client.interceptors.response.use(
  (res) => res,
  (err) => {
    const e = err.response?.data?.error;
    const message = e
      ? `${e.code}: ${e.message}`
      : err.code === "ERR_NETWORK"
        ? "Backend not reachable - start it with: uvicorn app.main:app --reload --port 8000"
        : err.message;
    return Promise.reject(new Error(message));
  }
);

export default client;