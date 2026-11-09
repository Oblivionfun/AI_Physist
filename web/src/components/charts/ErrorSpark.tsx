import { scaleLinear, scaleLog } from "d3-scale";
import { line } from "d3-shape";
import { runningMedian, type ExpRow } from "../../data/derive";

const LO = 0.03;
const HI = 30;

/**
 * Prediction error of each experiment in tolerances (log scale). Below the 1x line the
 * learner predicted within tolerance; diamonds are the referee's probes.
 */
export function ErrorSpark({
  rows,
  budget,
  width = 300,
  height = 96,
  selected,
  onSelect,
}: {
  rows: ExpRow[];
  budget: number;
  width?: number;
  height?: number;
  selected?: number;
  onSelect?: (index: number) => void;
}) {
  const m = { l: 30, r: 6, t: 6, b: 16 };
  const x = scaleLinear().domain([0, Math.max(budget, rows.length, 1) - 1]).range([m.l, width - m.r]);
  const y = scaleLog().domain([LO, HI]).range([height - m.b, m.t]).clamp(true);
  const errs = rows.map((r) => (r.kind === "null-wrong" ? HI : r.err == null ? null : Math.max(LO, r.err)));
  const med = runningMedian(errs);
  const path = line<number | null>()
    .defined((d) => d != null)
    .x((_, i) => x(rows[i].exp.index))
    .y((d) => y(d as number))(med);

  return (
    <svg width={width} height={height} className="chart" role="img" aria-label="预测误差随实验次数">
      {[0.1, 1, 10].map((t) => (
        <g key={t}>
          <line x1={m.l} x2={width - m.r} y1={y(t)} y2={y(t)} className={t === 1 ? "axis-key" : "axis-grid"} />
          <text x={m.l - 4} y={y(t) + 3} className="tick" textAnchor="end">
            {t}×
          </text>
        </g>
      ))}
      <text x={m.l} y={height - 3} className="tick">
        实验 1
      </text>
      <text x={width - m.r} y={height - 3} className="tick" textAnchor="end">
        {budget}
      </text>
      {path && <path d={path} className="median-line" />}
      {rows.map((r, i) => {
        const e = errs[i];
        if (e == null) return null;
        const cx = x(r.exp.index);
        const cy = y(e);
        const sel = selected === r.exp.index;
        const cls = `pt ${r.kind === "null-wrong" ? "kind" : ""} ${sel ? "sel" : ""}`;
        return r.exp.probe ? (
          <rect
            key={i}
            x={cx - 3.2}
            y={cy - 3.2}
            width={6.4}
            height={6.4}
            transform={`rotate(45 ${cx} ${cy})`}
            className={`${cls} probe`}
            onClick={() => onSelect?.(r.exp.index)}
          />
        ) : (
          <circle key={i} cx={cx} cy={cy} r={sel ? 3.6 : 2.4} className={cls} onClick={() => onSelect?.(r.exp.index)} />
        );
      })}
    </svg>
  );
}
