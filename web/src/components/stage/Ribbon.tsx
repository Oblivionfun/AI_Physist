import { scaleLinear, scaleLog } from "d3-scale";
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { expRows, roundsOf, tolerance } from "../../data/derive";
import type { RunState } from "../../data/fold";
import { toDisplay, toReal, type Timeline } from "../../data/timeline";
import type { Label } from "../../data/types";
import { useFullState } from "../../state/runState";
import { useStore } from "../../state/store";

const LANES: { id: "builder" | Label; name: string }[] = [
  { id: "builder", name: "建造者" },
  { id: "A", name: "学习者 A" },
  { id: "B", name: "学习者 B" },
];
const LANE_H = 26;
const TOP = 18;
const LEFT = 76;

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(800);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

interface Bar {
  lane: number;
  a: number;
  b: number;
}

function sessionBars(s: RunState, tl: Timeline): { bars: Bar[]; rounds: { r: number; x: number }[] } {
  const bars: Bar[] = [];
  const rounds: { r: number; x: number }[] = [];
  for (const rs of roundsOf(s)) {
    const first = rs.builderSessions[0]?.startTs ?? rs.attempts[0]?.ts ?? rs.cardTs;
    if (first) rounds.push({ r: rs.round, x: toDisplay(tl, first) });
    for (const b of rs.builderSessions) {
      bars.push({ lane: 0, a: toDisplay(tl, b.startTs), b: toDisplay(tl, b.endTs ?? s.lastTs) });
    }
    for (const label of ["A", "B"] as Label[]) {
      const ss = rs.sessions[label];
      if (!ss?.startTs) continue;
      const end = ss.endTs ?? s.lastTs;
      bars.push({ lane: label === "A" ? 1 : 2, a: toDisplay(tl, ss.startTs), b: toDisplay(tl, end) });
    }
  }
  return { bars, rounds };
}

export function Ribbon() {
  const s = useFullState();
  const tl = useStore((x) => x.timeline);
  const disp = useStore((x) => x.disp);
  const seekDisp = useStore((x) => x.seekDisp);
  const [ref, width] = useWidth();
  const height = TOP + LANES.length * LANE_H + 6;
  const x = scaleLinear().domain([0, Math.max(1, tl.duration)]).range([LEFT, width - 8]);
  const errY = scaleLog().domain([0.05, 20]).range([2, LANE_H - 6]).clamp(true);

  const marks = useMemo(() => sessionBars(s, tl), [s, tl]);

  const onPointer = (e: React.PointerEvent<SVGSVGElement>) => {
    if (e.buttons !== 1 && e.type !== "pointerdown") return;
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    seekDisp(x.invert(e.clientX - rect.left));
  };

  return (
    <section className="ribbon" ref={ref}>
      <svg width={width} height={height} onPointerDown={onPointer} onPointerMove={onPointer} role="slider" aria-label="时间轴" aria-valuenow={disp}>
        {LANES.map((l, i) => (
          <g key={l.id}>
            <line x1={LEFT} x2={width - 8} y1={TOP + i * LANE_H + LANE_H} y2={TOP + i * LANE_H + LANE_H} className="axis-grid" />
            <text x={8} y={TOP + i * LANE_H + LANE_H / 2 + 4} className="lane-name">
              {l.name}
            </text>
          </g>
        ))}
        {marks.rounds.map((r) => (
          <g key={r.r}>
            <line x1={x(r.x)} x2={x(r.x)} y1={4} y2={height} className="round-rule" />
            <text x={x(r.x) + 4} y={12} className="round-name">
              R{r.r}
            </text>
          </g>
        ))}
        {marks.bars.map((b, i) => (
          <rect key={i} x={x(b.a)} width={Math.max(1, x(b.b) - x(b.a))} y={TOP + b.lane * LANE_H + 4} height={LANE_H - 8} className="session-bar" />
        ))}
        <BuilderLane s={s} tl={tl} x={x} />
        {roundsOf(s).flatMap((rs) =>
          (["A", "B"] as Label[]).flatMap((label) => {
            const ss = rs.sessions[label];
            if (!ss) return [];
            const lane = label === "A" ? 1 : 2;
            const base = TOP + lane * LANE_H + LANE_H - 3;
            const tol = tolerance(rs);
            const ticks = expRows(ss, tol).map((row, i) => {
              const h = row.err == null ? LANE_H - 6 : errY(Math.max(0.05, row.err));
              const cx = x(toDisplay(tl, row.exp.ts));
              return (
                <line key={`e${rs.round}${label}${i}`} x1={cx} x2={cx} y1={base} y2={base - h} className={`err-tick ${row.exp.probe ? "probe" : ""}`} />
              );
            });
            const results = ss.results?.value;
            const answers = ss.answers.map((a, i) => {
              const ok = results?.[a.phase]?.[a.index]?.success;
              const cx = x(toDisplay(tl, a.ts));
              return (
                <rect
                  key={`a${rs.round}${label}${i}`}
                  x={cx - 2}
                  y={TOP + lane * LANE_H + 3}
                  width={4}
                  height={4}
                  className={`answer-tick ${ok == null ? "" : ok ? "hit" : "miss"} ${a.phase}`}
                />
              );
            });
            return [...ticks, ...answers];
          }),
        )}
        <rect x={x(disp)} width={Math.max(0, width - 8 - x(disp))} y={0} height={height} className="future" />
        <line x1={x(disp)} x2={x(disp)} y1={0} y2={height} className="playhead" />
        <PlayheadLabel tl={tl} disp={disp} x={x(disp)} width={width} start={s.startTs} />
      </svg>
    </section>
  );
}

function BuilderLane({ s, tl, x }: { s: RunState; tl: Timeline; x: (v: number) => number }) {
  const y = TOP + LANE_H / 2;
  return (
    <g>
      {roundsOf(s).flatMap((rs) => [
        ...rs.checks.map((c, i) => (
          <circle key={`c${rs.round}-${i}`} cx={x(toDisplay(tl, c.ts))} cy={y + 6} r={1.8} className={`check-dot ${c.result}`} />
        )),
        ...rs.attempts.map((a) => (
          <g key={`s${rs.round}-${a.attempt}`}>
            <rect
              x={x(toDisplay(tl, a.ts)) - 4}
              y={y - 8}
              width={8}
              height={8}
              transform={`rotate(45 ${x(toDisplay(tl, a.ts))} ${y - 4})`}
              className="submit-mark"
            />
            {a.cert && (
              <text x={x(toDisplay(tl, a.cert.ts))} y={y + 10} className={`cert-mark ${a.cert.passed ? "pass" : "fail"}`} textAnchor="middle">
                {a.cert.passed ? "✓" : "✕"}
              </text>
            )}
          </g>
        )),
        rs.reportTs ? (
          <line key={`r${rs.round}`} x1={x(toDisplay(tl, rs.reportTs))} x2={x(toDisplay(tl, rs.reportTs))} y1={y - 10} y2={y + 10} className="report-mark" />
        ) : null,
      ])}
    </g>
  );
}

/** Real run time at the playhead (the axis itself is squeezed display time). */
function PlayheadLabel({ tl, disp, x, width, start }: { tl: Timeline; disp: number; x: number; width: number; start: number }) {
  const real = toReal(tl, disp) - start;
  const h = Math.floor(real / 3600);
  const m = Math.floor((real % 3600) / 60);
  const text = `${h ? `${h}h` : ""}${m}m`;
  return (
    <text x={Math.min(x + 4, width - 40)} y={TOP - 4} className="playhead-label">
      {text}
    </text>
  );
}
