import { scaleLinear } from "d3-scale";
import type { SessionState } from "../../data/fold";

/** Each pretest and exam goal on the outcome axis, with the tolerance band and where it landed. */
export function ExamStrip({ ss, goal, tol, width = 360 }: { ss: SessionState; goal: [number, number]; tol: number; width?: number }) {
  const rows = [
    ...(ss.results?.value.pretest ?? []).map((r) => ({ ...r, phase: "前测" })),
    ...(ss.results?.value.exam ?? []).map((r) => ({ ...r, phase: "考试" })),
  ];
  if (!rows.length) return <p className="muted small">前测和考试结果在会话结束时才公布。</p>;
  const pad = (goal[1] - goal[0]) * 0.25;
  const m = { l: 64, r: 10 };
  const x = scaleLinear()
    .domain([goal[0] - pad, goal[1] + pad])
    .range([m.l, width - m.r]);
  const rowH = 15;
  const nPre = ss.results?.value.pretest.length ?? 0;
  return (
    <svg width={width} height={rows.length * rowH + 30} className="chart">
      <rect x={x(goal[0])} y={0} width={x(goal[1]) - x(goal[0])} height={rows.length * rowH + 6} className="goal-wash" />
      {rows.map((r, i) => {
        const y = i * rowH + 10 + (i >= nPre ? 8 : 0);
        const g = r.goal[0];
        const o = r.observed_outcome?.[0];
        return (
          <g key={i}>
            <text x={0} y={y + 4} className="row-name">
              {r.phase} {i >= nPre ? i - nPre + 1 : i + 1}
            </text>
            <line x1={x(g - tol)} x2={x(g + tol)} y1={y} y2={y} className="tol-seg" />
            <circle cx={x(g)} cy={y} r={2} className="goal-dot" />
            {o != null ? (
              <circle cx={x(Math.max(goal[0] - pad, Math.min(goal[1] + pad, o)))} cy={y} r={3.4} className={`land ${r.success ? "hit" : "miss"}`} />
            ) : (
              <text x={width - m.r} y={y + 4} className="tick miss-text" textAnchor="end">
                无落点
              </text>
            )}
          </g>
        );
      })}
      {x.ticks(5).map((t) => (
        <text key={t} x={x(t)} y={rows.length * rowH + 28} className="tick" textAnchor="middle">
          {t}
        </text>
      ))}
    </svg>
  );
}
