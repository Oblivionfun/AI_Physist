import { scaleLinear, scalePoint } from "d3-scale";
import type { RoundMetrics } from "../../data/metrics";
import { useSize } from "./useSize";

const BAND: [number, number] = [0.3, 0.8];

/**
 * The builder aims for a learner exam success inside the target band, harder than a
 * black-box fit can solve; each round shows where that landed.
 */
export function ArmsRace({ rounds }: { rounds: RoundMetrics[] }) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const m = { l: 44, r: 16, t: 12, b: 26 };
  const x = scalePoint<number>()
    .domain(rounds.map((r) => r.round))
    .range([m.l + 30, width - m.r - 30]);
  const y = scaleLinear().domain([0, 1]).range([height - m.b, m.t]);
  const pts = (key: "A" | "B") =>
    rounds
      .filter((r) => r.exam[key] != null)
      .map((r) => `${x(r.round)! + (key === "A" ? -6 : 6)},${y(r.exam[key]!)}`)
      .join(" ");
  return (
    <div ref={ref} className="chart-box tall">
      <svg width={width} height={height} className="chart">
        <rect x={m.l} width={width - m.l - m.r} y={y(BAND[1])} height={y(BAND[0]) - y(BAND[1])} className="band" />
        <text x={width - m.r} y={y(BAND[1]) - 4} className="tick" textAnchor="end">
          目标区间 30%–80%
        </text>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} className="axis-grid" />
            <text x={m.l - 4} y={y(t) + 3} className="tick" textAnchor="end">
              {Math.round(t * 100)}%
            </text>
          </g>
        ))}
        {rounds.map((r) => (
          <text key={r.round} x={x(r.round)} y={height - 8} className="round-name" textAnchor="middle">
            R{r.round}
          </text>
        ))}
        <polyline points={pts("A")} className="exam-line" />
        <polyline points={pts("B")} className="exam-line b" />
        {rounds.map((r) => {
          const cx = x(r.round)!;
          return (
            <g key={r.round}>
              {r.blackbox != null && <rect x={cx - 5} y={y(r.blackbox) - 5} width={10} height={10} className="bb-mark" />}
              {r.reference != null && (
                <path d={`M${cx} ${y(r.reference) - 6} l6 10 h-12 z`} className="ref-mark" transform={`translate(${-18} 0)`} />
              )}
              {(["A", "B"] as const).map((k) =>
                r.exam[k] != null ? <circle key={k} cx={cx + (k === "A" ? -6 : 6)} cy={y(r.exam[k]!)} r={4.5} className={`exam-dot ${k}`} /> : null,
              )}
              {(["A", "B"] as const).map((k) =>
                r.pretest[k] != null ? (
                  <circle key={`p${k}`} cx={cx + (k === "A" ? -6 : 6)} cy={y(r.pretest[k]!)} r={3} className="pre-dot" />
                ) : null,
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
