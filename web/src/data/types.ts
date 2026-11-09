/** Events produced by observatory/events.py. Field names mirror the Python side. */

export type Label = "A" | "B";
export type Theta = Record<string, number>;
export type Vec = number[];

export interface Knob {
  name: string;
  low: number;
  high: number;
  unit: string;
  description: string;
}

export interface ScenePart {
  name: string;
  shape: "box" | "sphere" | "capsule" | "cylinder";
  size: number[];
  material: string;
  hidden: boolean;
  hidden_mass?: string | null;
  moving: boolean;
  mount: string;
  pos: Vec;
  quat: Vec;
}

export interface Scene {
  name: string;
  parts: ScenePart[];
  outcome: { kind: string; part: string; axes: string[]; base: Vec };
  goal_space: [number, number][];
  tolerance: number;
  budget: number;
  horizon: number;
  knobs: Knob[];
  sensors: { name: string; kind: string; part: string; noise: number }[];
  hidden: string[];
  modifiable: { key: string; part: string; field: string; low: number; high: number }[];
  title: string;
  escalation: string[];
}

export interface Verdict {
  code: string;
  title: string;
  decision: string;
  value: number | null;
  threshold: number | null;
  detail: string;
}

export interface Unknown {
  name: string;
  description: string;
  low: number;
  high: number;
  unit: string;
  scope: "world" | "device";
}

export interface Card {
  version: number;
  title: string;
  goal_text: string;
  manual: string;
  knobs: Knob[];
  sensors: { name: string; kind: string; part: string; noise: number; rate_hz: number }[];
  unknowns: Unknown[];
  outcome: {
    kind: string;
    part: string;
    axes: string[];
    description: string;
    noise: number;
    goal_space: [number, number][];
    tolerance: number;
  };
  modifiable: { name: string; current: number; low: number; high: number }[];
  protocol: { pretest_goals: number; budget: number; probe_every: number; exam_goals: number; horizon: number };
  rules: string;
  changelog: string[];
}

export interface InstanceReport {
  label: Label;
  pretest_success: number;
  exam_success: number;
  experiments_used: number;
  budget: number;
  prediction_error_first_vs_last: [number | null, number | null];
  probe_errors_over_tol: (number | null)[];
  theory_hit_rates: Record<string, number | null>;
  non_discriminating_tests: string[];
  failure_tags: string[];
  invalid: string | null;
}

export interface Report {
  round: number;
  device_version: number;
  certificate: string[];
  reference_learner_success: number | null;
  oracle_success: number | null;
  instances: InstanceReport[];
  learnability: number | null;
  swap_test: Record<string, number | string | null>;
  old_theory_on_new_device: number | null;
  controls: { modification_effect_over_tol?: Record<string, number | null>; blackbox_exam_success?: number };
  tickets: { category: string; text: string }[];
  guidance: string;
}

export interface Experiment {
  session?: string;
  index: number;
  probe: boolean;
  knobs: Record<string, number>;
  prediction: number[] | null;
  outcome: number[] | null;
  status: string;
  times: number[];
  traces: Record<string, (number | number[])[]>;
  synthetic?: boolean;
}

export interface Attempt {
  phase: "pretest" | "exam";
  index: number;
  goal: number[];
  knobs: Record<string, number>;
  outcome: number[] | null;
  observed: number[] | null;
  status: string;
  success: boolean;
}

export interface LabRecord {
  index: number;
  probe: boolean;
  knobs: Record<string, number>;
  prediction: number[] | null;
  true_outcome: number[] | null;
  observed_outcome: number[] | null;
  status: string;
}

export interface Belief {
  estimates: Record<string, { value: number; low: number; high: number }>;
}

export interface SessionFinal {
  attempts: Attempt[];
  lab: LabRecord[];
  theory_code: string | null;
  belief: Belief | null;
}

export interface ResultRow {
  goal: number[];
  knobs: Record<string, number>;
  observed_outcome: number[] | null;
  status: string;
  success: boolean;
}

export interface RunEnd {
  run_id: string;
  builder: string;
  learner: string;
  profile: string;
  rounds: { round: number; status: string; version?: number; device?: string; attempts: unknown[] }[];
  isolation_audit: { clean: boolean; learner_side_hits: string[]; builder_side_hits: string[] };
  chain_ok: boolean;
  chain_entries: number;
}

interface Base {
  seq: number;
  ts: number;
  round: number | null;
  label: Label | null;
  agent: "builder" | "learner" | null;
  truth: boolean;
}

type E<K extends string, D> = Base & { kind: K; data: D };

export type RunEvent =
  | E<"run", { run_id: string }>
  | E<"world", { theta: Theta }>
  | E<"submission", { attempt: number; device: string; scene: Scene }>
  | E<"certificate", { attempt: number; passed: boolean; verdicts: Verdict[]; seconds: number | null; stats: Record<string, unknown> }>
  | E<"instances", { A: Theta; B: Theta }>
  | E<"card", { card: Card }>
  | E<"channel", { seq: number; route: string; channel: number; kind: string; hash: string; prev: string; summary: Record<string, unknown> }>
  | E<"report", { report: Report }>
  | E<"session_end", { instance: Label; calls: number; experiments: number; theory_sha: string; tickets: { category: string; text: string }[] }>
  | E<"agent_start", { session: string; model: string | null }>
  | E<"thought", { session: string; text: string }>
  | E<"say", { session: string; text: string }>
  | E<"tool", { session: string; tool: string; command: string; ok: boolean; output: string }>
  | E<"check", { session: string; result: string; verdicts: Verdict[]; detail: string }>
  | E<"goal", { session: string; phase: "pretest" | "exam"; index: number; goal: number[] }>
  | E<"answer", { session: string; phase: "pretest" | "exam"; index: number; knobs: Record<string, number> | null }>
  | E<"theory", { session: string; code: string | null; belief: Belief | null; source: string }>
  | E<"agent_end", { session: string; ok: boolean; seconds: number }>
  | E<"experiment", Experiment>
  | E<"results", { session: string; pretest: ResultRow[]; exam: ResultRow[] }>
  | E<"session_final", SessionFinal>
  | E<"note", { session: string; workspace: string; text: string }>
  | E<"run_end", RunEnd>
  | E<"audit", { viewer_tokens: number; hits: string[]; clean: boolean }>;

export type EventKind = RunEvent["kind"];

export interface Replay {
  fps: number;
  parts: string[];
  frames: number;
  pos_scale: number;
  data: string;
  outcome: number[] | null;
  status: string;
  t_outcome: number;
}

export interface CurveVariant {
  key: string | null;
  value: number | null;
  visible: Record<string, number>;
  current?: boolean;
  test?: boolean;
  truth: Record<Label, (number[] | null)[] | null>;
  theory: Record<Label, (number[] | null)[] | null>;
}

export interface Curves {
  knob: string;
  knobs: string[];
  xs: number[];
  fixed: Record<string, number>;
  variants: CurveVariant[];
  tolerance: number;
  goal_space: [number, number][];
}

export interface RunListing {
  run_id: string;
  source: "live" | "recorded";
  live?: boolean;
  ended?: boolean;
  path?: string;
  builder?: string | null;
  learner?: string | null;
  rerun_of?: string | null;
  rounds?: { round: number; status: string; device?: string }[];
}

export function assertNever(x: never): never {
  throw new Error(`unhandled variant: ${JSON.stringify(x)}`);
}
