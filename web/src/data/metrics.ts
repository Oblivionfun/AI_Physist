import { examScore, expRows, median, roundsOf, tolerance } from "./derive";
import type { RunState } from "./fold";
import type { Label } from "./types";

export interface RoundMetrics {
  round: number;
  device?: string;
  version?: number;
  exam: Partial<Record<Label, number>>;
  pretest: Partial<Record<Label, number>>;
  /** Median prediction error of the first five experiments, in tolerances. */
  early: Partial<Record<Label, number | null>>;
  blackbox?: number;
  reference?: number | null;
  swap?: Record<string, number | string | null>;
}

const EARLY_N = 5;

export function roundMetrics(s: RunState): RoundMetrics[] {
  return roundsOf(s)
    .filter((rs) => rs.card)
    .map((rs) => {
      const tol = tolerance(rs);
      const out: RoundMetrics = {
        round: rs.round,
        device: rs.card?.title,
        version: rs.version,
        exam: {},
        pretest: {},
        early: {},
        blackbox: rs.report?.controls.blackbox_exam_success,
        reference: rs.report?.reference_learner_success,
        swap: rs.report?.swap_test,
      };
      for (const label of ["A", "B"] as Label[]) {
        const ss = rs.sessions[label];
        const rep = rs.report?.instances.find((x) => x.label === label);
        const exam = rep?.exam_success ?? ratio(examScore(ss, "exam"));
        const pre = rep?.pretest_success ?? ratio(examScore(ss, "pretest"));
        if (exam != null) out.exam[label] = exam;
        if (pre != null) out.pretest[label] = pre;
        const rows = expRows(ss, tol).slice(0, EARLY_N);
        if (rows.length) out.early[label] = median(rows.map((r) => r.err ?? NaN));
      }
      return out;
    });
}

function ratio(x: { hits: number; total: number } | null): number | null {
  return x ? x.hits / x.total : null;
}

const NEXT_TIME = /^(what to do differently|next time|for next time|for the next (session|round|device)|lessons?)\b[^:]*:\s*/i;

/** Notebook bullets addressed to the next session ("Next time: ...", "What to do differently: ..."). */
export function nextTimeNotes(text: string): string[] {
  const bullets: string[] = [];
  for (const line of text.split("\n")) {
    if (line.startsWith("- ")) bullets.push(line.slice(2));
    else if (bullets.length && /^\s+\S/.test(line)) bullets[bullets.length - 1] += " " + line.trim();
  }
  return bullets.filter((b) => NEXT_TIME.test(b)).map((b) => b.replace(NEXT_TIME, "").replace(/\s+/g, " ").trim());
}
