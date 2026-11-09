import { extent } from "d3-array";
import { scaleLinear } from "d3-scale";
import type { ExpRow } from "../../data/derive";
import { useSize } from "./useSize";

/** Predicted against observed outcome; the band is the tolerance around perfect prediction. */
export function PredObs({
  rows,
  tol,
  goal,
  selected,
  onSelect,
}: {
  rows: ExpRow[];
  tol: number;
  goal: [number, number];
  selected?: number;
  onSelect?: (i: number) => void;
}) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const pts = rows.filter((r) => r.exp.prediction && r.exp.outcome);
  const vals = pts.flatMap((r) => [r.exp.prediction![0], r.exp.outcome![0]]);
  const [lo0, hi0] = extent([...vals, goal[0], goal[1]]) as [number, number];
  const pad = (hi0 - lo0) * 0.06 || 0.1;
  const lo = lo0 - pad;
  const hi = hi0 + pad;
  const m = { l: 40, r: 10, t: 8, b: 28 };
  const side = Math.max(60, Math.min(width - m.l - m.r, height - m.t - m.b));
  const x = scaleLinear().domain([lo, hi]).range([m.l, m.l + side]);
  const y = scaleLinear().domain([lo, hi]).range([m.t + side, m.t]);
  const n = Math.max(1, rows.length - 1);
  const ticks = x.ticks(5);

  return (
    <div ref={ref} className="chart-box">
      <svg width={width} height={height} className="chart">
        <rect x={x(goal[0])} y={m.t} width={x(goal[1]) - x(goal[0])} height={side} className="goal-wash" />
        <polygon
          points={[
            [x(lo), y(lo + tol)],
            [x(hi - tol), y(hi)],
            [x(hi), y(hi)],
            [x(hi), y(hi - tol)],
            [x(lo + tol), y(lo)],
            [x(lo), y(lo)],
          ]
            .map((p) => p.join(","))
            .join(" ")}
          className="tol-band"
        />
        <line x1={x(lo)} y1={y(lo)} x2={x(hi)} y2={y(hi)} className="axis-key" />
        {ticks.map((t) => (
          <g key={t}>
            <text x={x(t)} y={m.t + side + 12} className="tick" textAnchor="middle">
              {t}
            </text>
            <text x={m.l - 4} y={y(t) + 3} className="tick" textAnchor="end">
              {t}
            </text>
          </g>
        ))}
        <text x={m.l + side} y={m.t + side + 24} className="tick" textAnchor="end">
          观测落点 →
        </text>
        <text x={m.l - 30} y={m.t + 4} className="tick">
          预测
        </text>
        {pts.map((r) => {
          const sel = selected === r.exp.index;
          return (
            <circle
              key={r.exp.index}
              cx={x(r.exp.outcome![0])}
              cy={y(r.exp.prediction![0])}
              r={sel ? 5 : 3}
              className={`pt ${sel ? "sel" : ""} ${r.exp.probe ? "probe" : ""}`}
              style={{ fillOpacity: 0.2 + 0.8 * (r.exp.index / n) }}
              onClick={() => onSelect?.(r.exp.index)}
            >
              <title>{`#${r.exp.index + 1} 预测 ${r.exp.prediction![0].toFixed(3)} 观测 ${r.exp.outcome![0].toFixed(3)}`}</title>
            </circle>
          );
        })}
      </svg>
    </div>
  );
}
