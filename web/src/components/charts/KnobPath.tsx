import { deviation } from "d3-array";
import { scaleLinear } from "d3-scale";
import type { AnswerState, SessionState } from "../../data/fold";
import type { Knob } from "../../data/types";
import { useSize } from "./useSize";

/** Where in knob space the learner chose to experiment, in order; exam answers on top. */
export function KnobPath({
  ss,
  knobs,
  selected,
  onSelect,
}: {
  ss: SessionState;
  knobs: Knob[];
  selected?: number;
  onSelect?: (i: number) => void;
}) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const exps = ss.experiments;
  const spread = knobs.map((k) => (deviation(exps, (e) => e.knobs[k.name]) ?? 0) / (k.high - k.low || 1));
  const order = knobs.map((_, i) => i).sort((a, b) => spread[b] - spread[a]);
  const kx = knobs[order[0]];
  const ky = knobs.length > 1 ? knobs[order[1]] : undefined;
  const m = { l: 44, r: 10, t: 10, b: 28 };
  const x = scaleLinear().domain([kx.low, kx.high]).range([m.l, width - m.r]);
  const y = ky ? scaleLinear().domain([ky.low, ky.high]).range([height - m.b, m.t]) : null;
  const py = (k: Record<string, number>) => (y && ky ? y(k[ky.name]) : (height - m.b + m.t) / 2);
  const n = Math.max(1, exps.length - 1);
  const results = ss.results?.value;
  const exam = ss.answers.filter((a): a is AnswerState & { knobs: Record<string, number> } => a.phase === "exam" && !!a.knobs);

  return (
    <div ref={ref} className="chart-box">
      <svg width={width} height={height} className="chart">
        <rect x={m.l} y={m.t} width={width - m.l - m.r} height={height - m.t - m.b} className="frame" />
        {x.ticks(5).map((t) => (
          <text key={t} x={x(t)} y={height - m.b + 12} className="tick" textAnchor="middle">
            {t}
          </text>
        ))}
        <text x={width - m.r} y={height - 4} className="tick" textAnchor="end">
          {kx.name} →
        </text>
        {y?.ticks(4).map((t) => (
          <text key={t} x={m.l - 4} y={y(t) + 3} className="tick" textAnchor="end">
            {t}
          </text>
        ))}
        {ky && (
          <text x={4} y={m.t + 8} className="tick">
            {ky.name}
          </text>
        )}
        <polyline points={exps.map((e) => `${x(e.knobs[kx.name])},${py(e.knobs)}`).join(" ")} className="path-line" />
        {exps.map((e) => (
          <circle
            key={e.index}
            cx={x(e.knobs[kx.name])}
            cy={py(e.knobs)}
            r={selected === e.index ? 5 : 3}
            className={`pt ${selected === e.index ? "sel" : ""} ${e.probe ? "probe" : ""}`}
            style={{ fillOpacity: 0.2 + 0.8 * (e.index / n) }}
            onClick={() => onSelect?.(e.index)}
          >
            <title>{`#${e.index + 1} ${Object.entries(e.knobs)
              .map(([k, v]) => `${k}=${v.toFixed(3)}`)
              .join(" ")}`}</title>
          </circle>
        ))}
        {exam.map((a) => {
          const ok = results?.exam[a.index]?.success;
          const cx = x(a.knobs[kx.name]);
          const cy = py(a.knobs);
          return (
            <rect key={`x${a.index}`} x={cx - 4} y={cy - 4} width={8} height={8} className={`exam-mark ${ok == null ? "" : ok ? "hit" : "miss"}`}>
              <title>{`考试第 ${a.index + 1} 题`}</title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}
