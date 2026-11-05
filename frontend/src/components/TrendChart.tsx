import {
  CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { ControlSettings, Frame } from "../api/types";

export function TrendChart({ frames, settings }: { frames: Frame[]; settings?: ControlSettings }) {
  const data = frames.map((f) => ({
    t: f.record.timestamp.slice(11, 16),
    temperature: f.record.temperature_c,
    occupancy: f.record.occupancy,
  }));
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <figure className="h-64 rounded border bg-white p-2">
        <figcaption className="text-sm font-semibold">Temperature (°C)</figcaption>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" minTickGap={30} />
            <YAxis domain={["auto", "auto"]} unit="°C" width={55} />
            <Tooltip />
            <Legend />
            {settings && <ReferenceLine y={settings.lower_bound_c} strokeDasharray="4 4" label="lower" />}
            {settings && <ReferenceLine y={settings.upper_bound_c} strokeDasharray="4 4" label="upper" />}
            <Line type="monotone" dataKey="temperature" name="Temperature" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </figure>
      <figure className="h-64 rounded border bg-white p-2">
        <figcaption className="text-sm font-semibold">Occupancy (1 = occupied, 0 = unoccupied)</figcaption>
        <ResponsiveContainer width="100%" height="90%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" minTickGap={30} />
            <YAxis domain={[0, 1]} ticks={[0, 1]} width={30} />
            <Tooltip />
            <Line type="stepAfter" dataKey="occupancy" name="Occupancy" dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </figure>
    </div>
  );
}
