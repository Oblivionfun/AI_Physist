import type { RoundState, RunState, SessionState } from "./fold";
import type { Experiment, Label, LabRecord, Theta, Unknown } from "./types";

export const LABEL_NAME: Record<Label, string> = { A: "实例 A", B: "实例 B（孪生）" };

const CHECK_NAME: Record<string, string> = {
  "construction rules": "构造规则",
  "numerical stability": "数值稳定",
  "passive energy": "被动能量",
  physics: "物理合理性",
  "timestep convergence": "步长收敛",
  existence: "存在性",
  robustness: "稳健性",
  "necessity (nominal parameters)": "必要性 · 名义参数",
  "necessity (single fixed action)": "必要性 · 固定动作",
  "identifiability (posterior predictive)": "可辨识性",
  "learnability (gray-box reference learner)": "参考学习者",
  "modification test": "改装检验",
  "leak scan": "泄漏扫描",
  "recorded certificate": "沿用原证书",
};

export function checkName(title: string): string {
  return CHECK_NAME[title] ?? title;
}

export const DECISION_NAME: Record<string, string> = {
  pass: "通过",
  fail: "未通过",
  warn: "警告",
  borderline: "临界",
};

/** Prediction error in tolerances; a null prediction is correct exactly when nothing landed. */
export function predictionError(
  pred: number[] | null,
  obs: number[] | null,
  tol: number,
): { err: number | null; kind: "value" | "null-right" | "null-wrong" } {
  if (pred && obs) {
    let s = 0;
    for (let i = 0; i < pred.length; i++) s += (pred[i] - obs[i]) ** 2;
    return { err: Math.sqrt(s) / tol, kind: "value" };
  }
  if (!pred && !obs) return { err: 0, kind: "null-right" };
  return { err: null, kind: "null-wrong" };
}

export function median(xs: number[]): number | null {
  const v = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = v.length >> 1;
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
}

export function runningMedian(xs: (number | null)[], window = 7): (number | null)[] {
  return xs.map((_, i) => median(xs.slice(Math.max(0, i - window + 1), i + 1).filter((x): x is number => x != null)));
}

export function tolerance(rs: RoundState | undefined): number {
  return rs?.card?.outcome.tolerance ?? rs?.attempts.at(-1)?.scene.tolerance ?? 1;
}

export function certifiedScene(rs: RoundState | undefined) {
  if (!rs) return undefined;
  const passed = rs.attempts.find((a) => a.cert?.passed);
  return (passed ?? rs.attempts.at(-1))?.scene;
}

/** True outcome of each lab experiment, once the referee's session record is in. */
export function trueOutcomes(ss: SessionState | undefined): Map<number, LabRecord> {
  const m = new Map<number, LabRecord>();
  for (const x of ss?.final?.lab ?? []) m.set(x.index, x);
  return m;
}

export interface ExpRow {
  exp: Experiment & { ts: number };
  err: number | null;
  kind: "value" | "null-right" | "null-wrong";
}

export function expRows(ss: SessionState | undefined, tol: number): ExpRow[] {
  return (ss?.experiments ?? []).map((exp) => ({ exp, ...predictionError(exp.prediction, exp.outcome, tol) }));
}

export function examScore(ss: SessionState | undefined, phase: "pretest" | "exam"): { hits: number; total: number } | null {
  const rows = ss?.results?.value[phase] ?? ss?.final?.attempts.filter((a) => a.phase === phase);
  if (!rows || !rows.length) return null;
  return { hits: rows.filter((r) => r.success).length, total: rows.length };
}

export function fmt(x: number | null | undefined, digits = 3): string {
  if (x == null || !Number.isFinite(x)) return "—";
  return x.toFixed(digits);
}

export function pct(x: number | null | undefined): string {
  if (x == null || !Number.isFinite(x)) return "—";
  return `${Math.round(x * 100)}%`;
}

export function knobText(knobs: Record<string, number> | null | undefined): string {
  if (!knobs) return "—";
  return Object.entries(knobs)
    .map(([k, v]) => `${k}=${v.toFixed(3)}`)
    .join("  ");
}

export function elapsed(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(ss).padStart(2, "0")}` : `${m}:${String(ss).padStart(2, "0")}`;
}

export function roundsOf(s: RunState): RoundState[] {
  return [...s.rounds.values()].sort((a, b) => a.round - b.round);
}

/** Error of an estimate relative to the prior's width (what the referee calls unit error). */
export function unitError(value: number, truth: number, u: Unknown): number {
  return Math.abs(value - truth) / Math.max(1e-12, u.high - u.low);
}

export function truthOf(name: string, rs: RoundState | undefined, label: Label, world?: Theta): number | undefined {
  return rs?.instances?.[label]?.[name] ?? world?.[name];
}

export function modelShort(name: string | null | undefined): string {
  if (!name) return "—";
  return name.replace(/^llm-(builder|learner):cursor-agent:/, "").replace(/^cursor-agent:/, "");
}
