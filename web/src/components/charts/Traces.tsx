import { extent } from "d3-array";
import { scaleLinear } from "d3-scale";
import { line } from "d3-shape";
import type { Experiment } from "../../data/types";

const AXES = ["x", "y", "z"];

/** The sensor time series the learner actually received for one experiment (noisy). */
export function Traces({ exp, width = 360 }: { exp: Experiment; width?: number }) {
  const names = Object.keys(exp.traces);
  if (!exp.times.length || !names.length) return <p className="muted small">这次实验没有传感器数据（设计里没有传感器，或记录来自裁判汇总）。</p>;
  const rows = names.flatMap((n) => {
    const v = exp.traces[n];
    if (Array.isArray(v[0])) {
      return [0, 1, 2]
        .map((c) => ({ name: `${n}.${AXES[c]}`, ys: v.map((p) => (p as number[])[c]) }))
        .filter((r) => (extent(r.ys) as [number, number]).reduce((a, b) => b - a) > 1e-4);
    }
    return [{ name: n, ys: v as number[] }];
  });
  const rowH = 46;
  const m = { l: 92, r: 8 };
  const x = scaleLinear()
    .domain([0, exp.times[exp.times.length - 1] || 1])
    .range([m.l, width - m.r]);
  return (
    <svg width={width} height={rows.length * rowH + 14} className="chart">
      {rows.map((r, i) => {
        const [lo, hi] = extent(r.ys) as [number, number];
        const y = scaleLinear()
          .domain([lo, hi === lo ? lo + 1 : hi])
          .range([i * rowH + rowH - 8, i * rowH + 6]);
        const d = line<number>()
          .x((_, j) => x(exp.times[j]))
          .y((v) => y(v))(r.ys);
        return (
          <g key={r.name}>
            <text x={0} y={i * rowH + rowH / 2 + 2} className="row-name">
              {r.name}
            </text>
            <text x={m.l - 6} y={i * rowH + 12} className="tick" textAnchor="end">
              {hi.toFixed(2)}
            </text>
            <text x={m.l - 6} y={i * rowH + rowH - 8} className="tick" textAnchor="end">
              {lo.toFixed(2)}
            </text>
            <line x1={m.l} x2={width - m.r} y1={i * rowH + rowH - 2} y2={i * rowH + rowH - 2} className="axis-grid" />
            <path d={d ?? ""} className="trace-line" />
          </g>
        );
      })}
      <text x={width - m.r} y={rows.length * rowH + 10} className="tick" textAnchor="end">
        t / s →
      </text>
    </svg>
  );
}
