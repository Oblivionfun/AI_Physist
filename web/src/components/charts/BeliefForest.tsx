import { scaleLinear } from "d3-scale";
import type { Belief, Theta, Unknown } from "../../data/types";
import { unitError } from "../../data/derive";

/**
 * One row per unknown, each on its own prior range: the learner's 90 % interval (its own
 * report), and in the god view the true value. Unit error is |estimate − truth| / prior width.
 */
export function BeliefForest({
  unknowns,
  belief,
  truth,
  god,
  width = 360,
}: {
  unknowns: Unknown[];
  belief?: Belief | null;
  truth?: Theta;
  god: boolean;
  width?: number;
}) {
  const rowH = 20;
  const m = { l: 150, r: 46 };
  const groups: { scope: string; name: string; rows: Unknown[] }[] = [
    { scope: "world", name: "世界级（跨轮沿用）", rows: unknowns.filter((u) => u.scope === "world") },
    { scope: "device", name: "装置级（每个实例不同）", rows: unknowns.filter((u) => u.scope === "device") },
  ];
  const height = unknowns.length * rowH + groups.length * 18 + 8;
  const x = scaleLinear().domain([0, 1]).range([m.l, width - m.r]);
  let yCursor = 0;
  return (
    <svg width={width} height={height} className="chart forest">
      {groups.map((g) => {
        if (!g.rows.length) return null;
        const y0 = yCursor;
        yCursor += 18 + g.rows.length * rowH;
        return (
          <g key={g.scope} transform={`translate(0, ${y0})`}>
            <text x={0} y={12} className="group-name">
              {g.name}
            </text>
            {g.rows.map((u, i) => {
              const y = 18 + i * rowH + rowH / 2;
              const f = (v: number) => x((v - u.low) / (u.high - u.low || 1));
              const est = belief?.estimates[u.name];
              const t = truth?.[u.name];
              const err = est && t != null ? unitError(est.value, t, u) : null;
              return (
                <g key={u.name}>
                  <text x={0} y={y + 4} className="row-name">
                    {u.name}
                  </text>
                  <line x1={x(0)} x2={x(1)} y1={y} y2={y} className="prior-bar" />
                  {est && (
                    <>
                      <line x1={f(Math.max(u.low, est.low))} x2={f(Math.min(u.high, est.high))} y1={y} y2={y} className="belief-bar" />
                      <circle cx={f(est.value)} cy={y} r={3} className="belief-dot" />
                    </>
                  )}
                  {god && t != null && <line x1={f(t)} x2={f(t)} y1={y - 6} y2={y + 6} className="truth-tick" />}
                  <text x={width - 2} y={y + 4} className="tick" textAnchor="end">
                    {!est ? "未估计" : god && err != null ? err.toFixed(2) : ""}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}
