export function SimulationBanner() {
  return (
    <div role="note" className="bg-amber-100 border-b border-amber-300 px-4 py-2 text-sm text-amber-900">
      <strong>SIMULATION</strong> — recorded sensor data is replayed and HVAC outputs are simulated
      commands. Recorded temperatures do not respond to commands. Runtime differences are not
      measured energy savings.
    </div>
  );
}
