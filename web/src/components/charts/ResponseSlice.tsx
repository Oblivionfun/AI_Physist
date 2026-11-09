import { extent } from "d3-array";
import { scaleLinear } from "d3-scale";
import { line } from "d3-shape";
import type { SessionState } from "../../data/fold";
import type { Curves, CurveVariant, Label } from "../../data/types";
import { useSize } from "./useSize";

type Pt = [number, number];

function series(xs: number[], ys: (number[] | null)[] | null | undefined): Pt[][] {
  if (!ys) return [];
  const out: Pt[][] = [];
  let cur: Pt[] = [];
  ys.forEach((y, i) => {
    if (y && Number.isFinite(y[0])) cur.push([xs[i], y[0]]);
    else if (cur.length) {
      out.push(cur);
      cur = [];
    }
  });
  if (cur.length) out.push(cur);
  return out;
}

/**
 * Outcome along one knob with the others at the learner's usual setting: the true response
 * (god view), the learner's submitted theory, and the observations taken near this slice.
 * `variant` may be a publicly modified device, on which the theory was never trained.
 */
export function ResponseSlice({
  curves,
  variant,
  label,
  ss,
  god,
  ranges,
}: {
  curves: Curves;
  variant: CurveVariant;
  label: Label;
  ss?: SessionState;
  god: boolean;
  /** Width of each knob's range: observations within 6 % of the slice count as on it. */
  ranges: Record<string, number>;
}) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const base = curves.variants[0];
  const xs = curves.xs;
  const knob = curves.knob;
  const span = xs[xs.length - 1] - xs[0];
  const near = (ss?.experiments ?? []).filter((e) =>
    curves.knobs.every((k) => k === knob || Math.abs(e.knobs[k] - curves.fixed[k]) <= 0.06 * (ranges[k] || 1)),
  );
  const truth = series(xs, variant.truth[label]);
  const theory = series(xs, variant.theory[label]);
  const baseTruth = variant.key ? series(xs, base.truth[label]) : [];
  const all = [
    ...truth.flat().map((p) => p[1]),
    ...theory.flat().map((p) => p[1]),
    ...near.map((e) => e.outcome?.[0]).filter((v): v is number => v != null),
    ...curves.goal_space[0],
  ];
  const [lo, hi] = (extent(all) as [number, number]) ?? [0, 1];
  const pad = (hi - lo) * 0.08 || 0.1;
  const m = { l: 44, r: 10, t: 10, b: 28 };
  const x = scaleLinear().domain([xs[0], xs[0] + span]).range([m.l, width - m.r]);
  const y = scaleLinear().domain([lo - pad, hi + pad]).range([height - m.b, m.t]);
  const path = line<Pt>()
    .x((p) => x(p[0]))
    .y((p) => y(p[1]));
  const g = curves.goal_space[0];

  return (
    <div ref={ref} className="chart-box">
      <svg width={width} height={height} className="chart">
        <rect x={m.l} y={y(g[1])} width={width - m.l - m.r} height={y(g[0]) - y(g[1])} className="goal-wash" />
        {x.ticks(5).map((t) => (
          <text key={t} x={x(t)} y={height - m.b + 12} className="tick" textAnchor="middle">
            {t}
          </text>
        ))}
        {y.ticks(5).map((t) => (
          <g key={t}>
            <line x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} className="axis-grid" />
            <text x={m.l - 4} y={y(t) + 3} className="tick" textAnchor="end">
              {t}
            </text>
          </g>
        ))}
        <text x={width - m.r} y={height - 4} className="tick" textAnchor="end">
          {knob} →
        </text>
        {god && baseTruth.map((s, i) => <path key={`b${i}`} d={path(s) ?? ""} className="truth-line faint" />)}
        {god && truth.map((s, i) => <path key={`t${i}`} d={path(s) ?? ""} className="truth-line" />)}
        {theory.map((s, i) => (
          <path key={`h${i}`} d={path(s) ?? ""} className="theory-line" />
        ))}
        {!variant.key &&
          near.map((e) =>
            e.outcome ? <circle key={e.index} cx={x(e.knobs[knob])} cy={y(e.outcome[0])} r={2.6} className="obs-dot" /> : null,
          )}
      </svg>
    </div>
  );
}
