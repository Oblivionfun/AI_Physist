import { scaleLinear } from "d3-scale";
import { elapsed } from "../../data/derive";
import type { SessionState } from "../../data/fold";

/** The session's working rhythm: experiments, analysis code the learner wrote or ran, answers. */
export function Rhythm({ ss, width = 900 }: { ss: SessionState; width?: number }) {
  const t0 = ss.startTs ?? ss.experiments[0]?.ts ?? 0;
  const t1 = ss.endTs ?? Math.max(t0 + 1, ...ss.experiments.map((e) => e.ts), ...ss.answers.map((a) => a.ts));
  const m = { l: 70, r: 10 };
  const x = scaleLinear().domain([t0, t1]).range([m.l, width - m.r]);
  const analysis = ss.toolCalls.filter((c) => c.tool === "edit" || c.tool === "write" || /python|\.py\b/.test(c.command));
  const lanes = [
    { name: "实验", y: 12 },
    { name: "写/跑分析", y: 30 },
    { name: "前测/考试", y: 48 },
  ];
  return (
    <svg width={width} height={70} className="chart">
      {lanes.map((l) => (
        <g key={l.name}>
          <text x={0} y={l.y + 4} className="row-name">
            {l.name}
          </text>
          <line x1={m.l} x2={width - m.r} y1={l.y} y2={l.y} className="axis-grid" />
        </g>
      ))}
      {ss.experiments.map((e) => (
        <line key={e.index} x1={x(e.ts)} x2={x(e.ts)} y1={6} y2={18} className={`err-tick ${e.probe ? "probe" : ""}`} />
      ))}
      {analysis.map((c, i) => (
        <rect key={i} x={x(c.ts) - 2.5} y={27} width={5} height={6} className="analysis-mark">
          <title>{c.command}</title>
        </rect>
      ))}
      {ss.answers.map((a, i) => (
        <rect key={i} x={x(a.ts) - 2} y={45} width={4} height={6} className={`answer-tick ${a.phase}`} />
      ))}
      {ss.theory && <line x1={x(ss.theory.ts)} x2={x(ss.theory.ts)} y1={2} y2={56} className="report-mark" />}
      <text x={m.l} y={68} className="tick">
        0:00
      </text>
      <text x={width - m.r} y={68} className="tick" textAnchor="end">
        {elapsed(t1 - t0)}
      </text>
    </svg>
  );
}
