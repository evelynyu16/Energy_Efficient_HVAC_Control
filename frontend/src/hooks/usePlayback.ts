import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Frame, ManualMode, RuntimeReport, SessionState } from "../api/types";

const TICK_MS = 500; // one step request per tick; well under the 1 s display requirement
const MAX_FRAMES = 720; // rolling chart window

/**
 * Owns the live session: the backend is the source of truth for controller state; this hook only
 * asks it to advance while RUNNING and keeps a rolling buffer of frames for the charts.
 */
export function usePlayback() {
  const [state, setState] = useState<SessionState | null>(null);
  const [frames, setFrames] = useState<Frame[]>([]);
  const [report, setReport] = useState<RuntimeReport | null>(null);
  const [speed, setSpeed] = useState(5);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const guard = useCallback(async <T,>(fn: () => Promise<T>) => {
    try {
      setError(null);
      return await fn();
    } catch (e) {
      setError((e as Error).message);
      return undefined;
    }
  }, []);

  const start = useCallback(async () => {
    await guard(async () => {
      let s = state;
      if (!s || s.status === "ENDED" || s.status === "COMPLETED") {
        s = await api.startSession();
        setFrames([]);
        setReport(null);
      }
      setState(await api.play(s.session_id));
    });
  }, [guard, state]);

  const pause = useCallback(async () => {
    if (state) await guard(async () => setState(await api.pause(state.session_id)));
  }, [guard, state]);

  const reset = useCallback(async () => {
    await guard(async () => {
      const s = await api.startSession(); // backend ends the previous session, keeps its logs
      setState(s);
      setFrames([]);
      setReport(null);
    });
  }, [guard]);

  const end = useCallback(async () => {
    if (!state) return;
    await guard(async () => {
      setReport(await api.end(state.session_id));
      setState(await api.state(state.session_id));
    });
  }, [guard, state]);

  const manual = useCallback(async (mode: ManualMode, reason: string) => {
    if (!state) return;
    await guard(async () => {
      await api.manual(state.session_id, mode, reason);
      setState(await api.state(state.session_id));
    });
  }, [guard, state]);

  const auto = useCallback(async (reason: string) => {
    if (!state) return;
    await guard(async () => {
      await api.auto(state.session_id, reason);
      setState(await api.state(state.session_id));
    });
  }, [guard, state]);

  useEffect(() => {
    if (state?.status !== "RUNNING") return;
    const id = state.session_id;
    const timer = setInterval(async () => {
      if (inFlight.current) return;
      inFlight.current = true;
      try {
        const res = await api.step(id, speed);
        setFrames((prev) => [...prev, ...res.frames].slice(-MAX_FRAMES));
        setState(res.state);
        if (res.state.status === "COMPLETED") setReport(await api.report(id));
      } catch (e) {
        setError((e as Error).message);
      } finally {
        inFlight.current = false;
      }
    }, TICK_MS);
    return () => clearInterval(timer);
  }, [state?.status, state?.session_id, speed]);

  return { state, frames, report, speed, setSpeed, error, start, pause, reset, end, manual, auto };
}
