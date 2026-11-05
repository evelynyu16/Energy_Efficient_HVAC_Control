import { NavLink, Route, Routes } from "react-router-dom";
import { SimulationBanner } from "./components/SimulationBanner";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SettingsPage } from "./pages/SettingsPage";

const link = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded ${isActive ? "bg-slate-800 text-white" : "hover:bg-slate-200"}`;

export default function App() {
  return (
    <div className="min-h-screen">
      <SimulationBanner />
      <header className="flex flex-wrap items-center gap-2 border-b bg-white px-4 py-2">
        <span className="mr-4 font-bold">Occupancy-Aware HVAC Control Simulator</span>
        <nav className="flex gap-1 text-sm" aria-label="Main">
          <NavLink to="/" end className={link}>Dashboard</NavLink>
          <NavLink to="/settings" className={link}>Settings</NavLink>
          <NavLink to="/history" className={link}>History &amp; Report</NavLink>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl p-4">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/history" element={<HistoryPage />} />
        </Routes>
      </main>
    </div>
  );
}
