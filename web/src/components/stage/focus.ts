import { certifiedScene } from "../../data/derive";
import type { AnswerState, RoundState, RunState, SessionState } from "../../data/fold";
import type { Experiment, Label, Scene } from "../../data/types";

export type StageAction =
  | { kind: "lab"; exp: Experiment & { ts: number } }
  | { kind: "pretest" | "exam"; answer: AnswerState };

export interface StageFocus {
  round?: number;
  rs?: RoundState;
  scene?: Scene;
  /** The scene is a submission still being certified (or rejected), not the certified device. */
  candidate: boolean;
  label?: Label;
  ss?: SessionState;
  action?: StageAction;
}

function latestAction(ss: SessionState | undefined): StageAction | undefined {
  if (!ss) return undefined;
  const exp = ss.experiments.at(-1);
  const ans = ss.answers.at(-1);
  if (exp && (!ans || exp.ts >= ans.ts)) return { kind: "lab", exp };
  if (ans) return { kind: ans.phase, answer: ans };
  return undefined;
}

export function stageFocus(s: RunState): StageFocus {
  const p = s.phase;
  const latestRound = Math.max(0, ...s.rounds.keys());
  const r =
    p.kind === "building" || p.kind === "certifying" || p.kind === "rejected" || p.kind === "learning" || p.kind === "reported"
      ? p.round
      : latestRound || undefined;
  if (r == null) return { candidate: false };
  const rs = s.rounds.get(r);
  if (p.kind === "certifying" || p.kind === "rejected" || (p.kind === "building" && rs?.attempts.length)) {
    const a = rs?.attempts.at(-1);
    return { round: r, rs, scene: a?.scene, candidate: !a?.cert?.passed };
  }
  if (p.kind === "building") {
    const prev = [...s.rounds.values()].filter((x) => x.round < r && x.card).at(-1);
    return { round: r, rs, scene: certifiedScene(prev), candidate: false };
  }
  const label: Label | undefined = p.kind === "learning" ? p.label : rs?.sessions.B ? "B" : rs?.sessions.A ? "A" : undefined;
  const ss = label ? rs?.sessions[label] : undefined;
  return { round: r, rs, scene: certifiedScene(rs), candidate: false, label, ss, action: latestAction(ss) };
}
