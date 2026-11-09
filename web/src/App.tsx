import { useEffect } from "react";
import { AccumulationView } from "./components/lenses/AccumulationView";
import { LearningView } from "./components/lenses/LearningView";
import { Header } from "./components/Header";
import { StageView } from "./components/stage/StageView";
import { ConclusionView } from "./components/tour/ConclusionView";
import { TourOverlay } from "./components/tour/TourOverlay";
import { listRuns, openSource, readToken } from "./data/source";
import type { RunListing } from "./data/types";
import { assertNever } from "./data/types";
import { RunStateProvider } from "./state/runState";
import { useStore, type View } from "./state/store";

function pickInitial(runs: RunListing[]): RunListing | undefined {
  const want = new URLSearchParams(window.location.search).get("run");
  return (
    runs.find((r) => r.run_id === want) ??
    runs.find((r) => r.source === "live" && r.live) ??
    runs.find((r) => r.source === "recorded" && r.run_id === "demo-2") ??
    runs.find((r) => r.source === "recorded") ??
    runs[0]
  );
}

function usePlaybackClock() {
  const tick = useStore((s) => s.tick);
  useEffect(() => {
    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      tick((now - last) / 1000);
      last = now;
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [tick]);
}

function CurrentView({ view }: { view: View }) {
  switch (view) {
    case "stage":
      return <StageView />;
    case "learning":
      return <LearningView />;
    case "accumulation":
      return <AccumulationView />;
    case "conclusion":
      return <ConclusionView />;
    default:
      return assertNever(view);
  }
}

export function App() {
  const listing = useStore((s) => s.listing);
  const source = useStore((s) => s.source);
  const view = useStore((s) => s.view);
  const runs = useStore((s) => s.runs);
  usePlaybackClock();

  useEffect(() => {
    const token = readToken();
    useStore.setState({ token });
    listRuns(token).then((list) => {
      useStore.getState().setRuns(list);
      const first = pickInitial(list);
      if (first) useStore.getState().open(first, openSource(first, token));
    });
  }, []);

  useEffect(() => {
    if (!source) return;
    const { addEvents, setStatus } = useStore.getState();
    return source.subscribe(addEvents, setStatus);
  }, [source]);

  return (
    <RunStateProvider>
      <div className="app">
        <Header />
        <main className="app-main">
          {listing ? (
            <CurrentView view={view} />
          ) : (
            <div className="empty">
              <p className="label">没有可显示的运行</p>
              <p className="muted">
                {runs.length === 0
                  ? "先用 `uv run observatory export <run_id>` 导出一个运行，或用 `uv run observatory serve` 打开直播。"
                  : "正在载入…"}
              </p>
            </div>
          )}
        </main>
        <TourOverlay />
      </div>
    </RunStateProvider>
  );
}
