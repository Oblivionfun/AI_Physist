import { create } from "zustand";
import { sortEvents } from "../data/fold";
import type { RunSource, StreamStatus } from "../data/source";
import { buildTimeline, toDisplay, type Timeline } from "../data/timeline";
import type { Label, RunEvent, RunListing } from "../data/types";

export type View = "stage" | "learning" | "accumulation" | "conclusion";

export interface Focus {
  round?: number;
  label?: Label;
  exp?: number;
}

interface Store {
  token: string | null;
  runs: RunListing[];
  listing?: RunListing;
  source?: RunSource;
  status: StreamStatus;
  events: RunEvent[];
  timeline: Timeline;
  disp: number;
  playing: boolean;
  speed: number;
  follow: boolean;
  god: boolean;
  view: View;
  focus: Focus;
  tour: { on: boolean; step: number };

  setRuns(runs: RunListing[]): void;
  open(listing: RunListing, source: RunSource): void;
  addEvents(batch: RunEvent[]): void;
  setStatus(s: StreamStatus): void;
  seekDisp(d: number): void;
  seekReal(ts: number): void;
  tick(dtSeconds: number): void;
  setPlaying(p: boolean): void;
  setSpeed(s: number): void;
  setFollow(f: boolean): void;
  setGod(g: boolean): void;
  setView(v: View): void;
  setFocus(f: Focus): void;
  setTour(t: { on: boolean; step: number }): void;
}

const EMPTY: Timeline = { real: [], disp: [], duration: 0 };

export const useStore = create<Store>((set, get) => ({
  token: null,
  runs: [],
  status: "closed",
  events: [],
  timeline: EMPTY,
  disp: 0,
  playing: false,
  speed: 30,
  follow: false,
  god: false,
  view: "stage",
  focus: {},
  tour: { on: false, step: 0 },

  setRuns: (runs) => set({ runs }),
  open: (listing, source) =>
    set({
      listing,
      source,
      events: [],
      timeline: EMPTY,
      disp: 0,
      playing: false,
      follow: source.live,
      god: !source.live,
      focus: {},
      tour: { on: false, step: 0 },
    }),
  addEvents: (batch) => {
    if (!batch.length) return;
    const { events, follow, disp, timeline } = get();
    const last = events.length ? events[events.length - 1] : undefined;
    const ordered = !last || batch.every((e, i) => e.ts >= (i ? batch[i - 1].ts : last.ts));
    const next = ordered ? [...events, ...batch] : sortEvents([...events, ...batch]);
    const tl = buildTimeline(next.map((e) => e.ts));
    const atEnd = disp >= timeline.duration - 1e-6;
    set({ events: next, timeline: tl, disp: follow || (atEnd && !events.length) ? tl.duration : disp });
  },
  setStatus: (status) => set({ status }),
  seekDisp: (d) => {
    const { timeline } = get();
    set({ disp: Math.max(0, Math.min(timeline.duration, d)), follow: false });
  },
  seekReal: (ts) => {
    const { timeline } = get();
    set({ disp: toDisplay(timeline, ts), follow: false });
  },
  tick: (dt) => {
    const { playing, speed, disp, timeline, follow } = get();
    if (follow) {
      if (disp !== timeline.duration) set({ disp: timeline.duration });
      return;
    }
    if (!playing) return;
    const d = disp + dt * speed;
    if (d >= timeline.duration) set({ disp: timeline.duration, playing: false });
    else set({ disp: d });
  },
  setPlaying: (playing) => {
    const { disp, timeline } = get();
    set({ playing, follow: false, disp: playing && disp >= timeline.duration ? 0 : disp });
  },
  setSpeed: (speed) => set({ speed }),
  setFollow: (follow) => set((s) => ({ follow, playing: false, disp: follow ? s.timeline.duration : s.disp })),
  setGod: (god) => set({ god }),
  setView: (view) => set({ view }),
  setFocus: (focus) => set({ focus }),
  setTour: (tour) => set({ tour }),
}));
