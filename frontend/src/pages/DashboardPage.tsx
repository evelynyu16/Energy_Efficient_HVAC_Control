import { ManualControl } from "../components/ManualControl";
import { PlaybackControls } from "../components/PlaybackControls";
import { RuntimeComparison } from "../components/RuntimeComparison";
import { SensorReadout } from "../components/SensorReadout";
import { TrendChart } from "../components/TrendChart";
import { usePlayback } from "../hooks/usePlayback";

export function DashboardPage() {
  const p = usePlayback();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <PlaybackControls
        state={p.state} speed={p.speed} onSpeed={p.setSpeed}
        onStart={p.start} onPause={p.pause} onReset={p.reset} onEnd={p.end}
      />
      {p.error && <p role="alert" className="text-rose-700">Error: {p.error}</p>}
      <SensorReadout frame={p.state?.current ?? null} />
      <ManualControl state={p.state} onManual={p.manual} onAuto={p.auto} />
      <TrendChart frames={p.frames} settings={p.state?.settings} />
      {p.report && <RuntimeComparison report={p.report} />}
    </div>
  );
}
