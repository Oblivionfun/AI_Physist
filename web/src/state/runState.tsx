import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { emptyState, fold, upperBound, type RunState } from "../data/fold";
import { decodeReplay, type DecodedReplay } from "../data/replay";
import { toReal } from "../data/timeline";
import type { Curves, Label } from "../data/types";
import { useStore } from "./store";

const CursorCtx = createContext<RunState>(emptyState());
const FullCtx = createContext<RunState>(emptyState());

/** Stage views show the run as of the playhead; analysis views show everything known so far. */
export function RunStateProvider({ children }: { children: ReactNode }) {
  const events = useStore((s) => s.events);
  const k = useStore((s) => upperBound(s.events, toReal(s.timeline, s.disp)));
  const cursor = useMemo(() => fold(events, k), [events, k]);
  const full = useMemo(() => fold(events), [events]);
  return (
    <FullCtx.Provider value={full}>
      <CursorCtx.Provider value={cursor}>{children}</CursorCtx.Provider>
    </FullCtx.Provider>
  );
}

export const useCursorState = () => useContext(CursorCtx);
export const useFullState = () => useContext(FullCtx);
export const useCursorTs = () => useStore((s) => toReal(s.timeline, s.disp));

export function useReplay(round?: number, label?: Label, kind?: string, index?: number): DecodedReplay | null {
  const source = useStore((s) => s.source);
  const [rep, setRep] = useState<DecodedReplay | null>(null);
  useEffect(() => {
    setRep(null);
    if (!source || round == null || !label || !kind || index == null) return;
    let alive = true;
    source.replay(round, label, kind, index).then((r) => {
      if (alive) setRep(r ? decodeReplay(r) : null);
    });
    return () => {
      alive = false;
    };
  }, [source, round, label, kind, index]);
  return rep;
}

export function useCurves(round?: number, knob?: string, refreshKey?: unknown): Curves | null | "loading" {
  const source = useStore((s) => s.source);
  const [c, setC] = useState<Curves | null | "loading">("loading");
  useEffect(() => {
    setC("loading");
    if (!source || round == null) return;
    let alive = true;
    source.curves(round, knob).then((x) => {
      if (alive) setC(x);
    });
    return () => {
      alive = false;
    };
  }, [source, round, knob, refreshKey]);
  return c;
}
