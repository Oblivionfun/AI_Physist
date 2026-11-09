import { scaleLinear, scaleLog, scalePoint } from "d3-scale";
import { modelShort } from "../../data/derive";
import type { RoundMetrics } from "../../data/metrics";
import type { RelatedRun } from "../../state/related";

type Pick = (r: RoundMetrics) => number | null | undefined;

const STYLE = ["solid", "dash", "dot", "dashdot"];

function Small({ runs, title, pick, log, width = 260, height = 150 }: { runs: RelatedRun[]; title: string; pick: Pick; log?: boolean; width?: number; height?: number }) {
  const rounds = [...new Set(runs.flatMap((r) => r.metrics.map((m) => m.round)))].sort((a, b) => a - b);
  const m = { l: 36, r: 8, t: 18, b: 20 };
  const x = scalePoint<number>().domain(rounds).range([m.l + 10, width - m.r - 10]);
  const y = log ? scaleLog().domain([0.1, 50]).range([height - m.b, m.t]).clamp(true) : scaleLinear().domain([0, 1]).range([height - m.b, m.t]);
  const ticks = log ? [0.1, 1, 10] : [0, 0.5, 1];
  return (
    <svg width={width} height={height} className="chart small-multiple">
      <text x={0} y={11} className="group-name">
        {title}
      </text>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} className={log && t === 1 ? "axis-key" : "axis-grid"} />
          <text x={m.l - 4} y={y(t) + 3} className="tick" textAnchor="end">
            {log ? `${t}×` : `${t * 100}%`}
          </text>
        </g>
      ))}
      {rounds.map((r) => (
        <text key={r} x={x(r)} y={height - 5} className="tick" textAnchor="middle">
          R{r}
        </text>
      ))}
      {runs.map((run, i) => {
        const pts = run.metrics
          .map((mm) => [mm.round, pick(mm)] as const)
          .filter((p): p is readonly [number, number] => p[1] != null && Number.isFinite(p[1]));
        return (
          <g key={run.run_id} className={`run-line ${STYLE[i % STYLE.length]}`}>
            <polyline points={pts.map(([r, v]) => `${x(r)},${y(Math.max(log ? 0.1 : 0, v))}`).join(" ")} />
            {pts.map(([r, v]) => (
              <circle key={r} cx={x(r)} cy={y(Math.max(log ? 0.1 : 0, v))} r={2.6} />
            ))}
          </g>
        );
      })}
    </svg>
  );
}

const mean = (a?: number, b?: number) => (a == null && b == null ? null : ((a ?? b)! + (b ?? a)!) / 2);

export function RunCompare({ runs }: { runs: RelatedRun[] }) {
  return (
    <div className="compare">
      <ul className="compare-legend">
        {runs.map((r, i) => (
          <li key={r.run_id} className={`run-line ${STYLE[i % STYLE.length]}`}>
            <svg width={26} height={8}>
              <line x1={0} x2={26} y1={4} y2={4} />
            </svg>
            <span className="mono">{r.run_id}</span> <span className="muted">{r.role} · {modelShort(r.learner)}</span>
          </li>
        ))}
      </ul>
      <div className="compare-grid">
        <Small runs={runs} title="考试命中率（A、B 平均）" pick={(m) => mean(m.exam.A, m.exam.B)} />
        <Small runs={runs} title="前测命中率（实例 A）" pick={(m) => m.pretest.A} />
        <Small runs={runs} title="前 5 次实验预测误差（实例 A）" pick={(m) => m.early.A} log />
      </div>
    </div>
  );
}
