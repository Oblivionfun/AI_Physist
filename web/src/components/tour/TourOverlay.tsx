import { useEffect, useMemo } from "react";
import { useFullState } from "../../state/runState";
import { useStore } from "../../state/store";
import { buildBeats, type Beat } from "./beats";

function go(beat: Beat) {
  const st = useStore.getState();
  st.setView(beat.view);
  if (beat.focus) st.setFocus(beat.focus);
  if (beat.at != null) st.seekReal(beat.at);
  if (beat.play) {
    st.setSpeed(beat.play);
    useStore.setState({ playing: true, follow: false });
  } else {
    useStore.setState({ playing: false });
  }
}

export function TourOverlay() {
  const tour = useStore((s) => s.tour);
  const setTour = useStore((s) => s.setTour);
  const full = useFullState();
  const beats = useMemo(() => buildBeats(full), [full]);
  const step = Math.min(tour.step, Math.max(0, beats.length - 1));
  const beat = beats[step];

  useEffect(() => {
    if (tour.on && beat) go(beat);
    // Only the step decides where to go; new events must not yank the view back.
  }, [tour.on, step]);

  useEffect(() => {
    if (!tour.on) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") setTour({ on: true, step: Math.min(beats.length - 1, step + 1) });
      else if (e.key === "ArrowLeft") setTour({ on: true, step: Math.max(0, step - 1) });
      else if (e.key === "Escape") setTour({ on: false, step });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [tour.on, step, beats.length, setTour]);

  if (!tour.on || !beat) return null;
  return (
    <aside className="tour" aria-live="polite">
      <p className="label">
        导览 <span className="mono">
          {step + 1} / {beats.length}
        </span>
      </p>
      <h2>{beat.title}</h2>
      <p>{beat.body}</p>
      <div className="tour-nav">
        <button className="btn" disabled={step === 0} onClick={() => setTour({ on: true, step: step - 1 })}>
          ← 上一步
        </button>
        <button className="btn play" disabled={step >= beats.length - 1} onClick={() => setTour({ on: true, step: step + 1 })}>
          下一步 →
        </button>
        <button className="btn" onClick={() => setTour({ on: false, step })}>
          结束
        </button>
        <span className="muted small">方向键翻页，Esc 退出；字幕由运行数据生成</span>
      </div>
    </aside>
  );
}
