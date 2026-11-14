// TEMPORARY App for Batch 4 - the final App.jsx comes in Batch 5
import { Route, Routes } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import Alarms from "./pages/Alarms";
import Checklist from "./pages/Checklist";
import Dashboard from "./pages/Dashboard";
import DataQuality from "./pages/DataQuality";
import FloodsNuisance from "./pages/FloodsNuisance";
import Incidents from "./pages/Incidents";
import IncidentTrace from "./pages/IncidentTrace";
import RepeatedUnsafe from "./pages/RepeatedUnsafe";

export default function App() {
  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/checklist" element={<Checklist />} />
          <Route path="/alarms" element={<Alarms />} />
          <Route path="/floods" element={<FloodsNuisance />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:id" element={<IncidentTrace />} />
          <Route path="/unsafe" element={<RepeatedUnsafe />} />
          <Route path="/quality" element={<DataQuality />} />
          <Route path="*" element={<div className="empty">This page arrives in the next batch</div>} />
        </Routes>
      </main>
    </div>
  );
}