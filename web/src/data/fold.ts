import {
  assertNever,
  type Belief,
  type Card,
  type Experiment,
  type Label,
  type Report,
  type ResultRow,
  type RunEnd,
  type RunEvent,
  type Scene,
  type SessionFinal,
  type Theta,
  type Verdict,
} from "./types";

export interface Timed<T> {
  ts: number;
  value: T;
}

export interface AttemptState {
  attempt: number;
  ts: number;
  scene: Scene;
  device: string;
  cert?: { ts: number; passed: boolean; verdicts: Verdict[]; seconds: number | null };
}

export interface AnswerState {
  ts: number;
  phase: "pretest" | "exam";
  index: number;
  knobs: Record<string, number> | null;
  goal: number[] | null;
}

export type LearnerStep = "pretest" | "lab" | "theory" | "exam" | "report" | "done";

export interface SessionState {
  label: Label;
  round: number;
  tag?: string;
  model?: string | null;
  startTs?: number;
  endTs?: number;
  step: LearnerStep;
  experiments: (Experiment & { ts: number })[];
  goals: { pretest: number[][]; exam: number[][] };
  answers: AnswerState[];
  theory?: Timed<{ code: string | null; belief: Belief | null }>;
  results?: Timed<{ pretest: ResultRow[]; exam: ResultRow[] }>;
  final?: SessionFinal;
  tickets: { category: string; text: string }[];
  notes: Timed<string>[];
  toolCalls: { ts: number; tool: string; command: string }[];
  thoughts: number;
}

export interface CheckState {
  ts: number;
  result: string;
  verdicts: Verdict[];
  detail: string;
}

export interface RoundState {
  round: number;
  attempts: AttemptState[];
  version?: number;
  card?: Card;
  cardTs?: number;
  instances?: { A: Theta; B: Theta };
  sessions: Partial<Record<Label, SessionState>>;
  report?: Report;
  reportTs?: number;
  builderSessions: { session: string; startTs: number; endTs?: number }[];
  checks: CheckState[];
  says: Timed<string>[];
}

export interface AgentTrack {
  session?: string;
  model?: string | null;
  active: boolean;
  since?: number;
  thought?: Timed<string>;
  say?: Timed<string>;
  tool?: Timed<{ tool: string; command: string; ok: boolean }>;
}

export interface ChannelEntry {
  ts: number;
  seq: number;
  route: string;
  channel: number;
  kind: string;
  hash: string;
  summary: Record<string, unknown>;
}

export type Phase =
  | { kind: "idle" }
  | { kind: "building"; round: number }
  | { kind: "certifying"; round: number; attempt: number }
  | { kind: "rejected"; round: number; attempt: number }
  | { kind: "learning"; round: number; label: Label; step: LearnerStep }
  | { kind: "reported"; round: number }
  | { kind: "ended" };

export interface RunState {
  runId: string;
  startTs: number;
  lastTs: number;
  world?: Theta;
  rounds: Map<number, RoundState>;
  builder: AgentTrack;
  learner: AgentTrack & { label?: Label; round?: number };
  channel: ChannelEntry[];
  phase: Phase;
  end?: RunEnd;
  audit?: { clean: boolean; hits: string[]; viewer_tokens: number };
}

export function emptyState(): RunState {
  return {
    runId: "",
    startTs: 0,
    lastTs: 0,
    rounds: new Map(),
    builder: { active: false },
    learner: { active: false },
    channel: [],
    phase: { kind: "idle" },
  };
}

function round(s: RunState, r: number): RoundState {
  let x = s.rounds.get(r);
  if (!x) {
    x = { round: r, attempts: [], sessions: {}, builderSessions: [], checks: [], says: [] };
    s.rounds.set(r, x);
  }
  return x;
}

function session(s: RunState, r: number, label: Label): SessionState {
  const rs = round(s, r);
  let x = rs.sessions[label];
  if (!x) {
    x = {
      label,
      round: r,
      step: "pretest",
      experiments: [],
      goals: { pretest: [], exam: [] },
      answers: [],
      tickets: [],
      notes: [],
      toolCalls: [],
      thoughts: 0,
    };
    rs.sessions[label] = x;
  }
  return x;
}

function learnerPhase(s: RunState, r: number, label: Label, step: LearnerStep) {
  session(s, r, label).step = step;
  s.phase = { kind: "learning", round: r, label, step };
}

/** Fold events (sorted by time) into the state of the run at the time of the last one. */
export function fold(events: RunEvent[], upTo = events.length): RunState {
  const s = emptyState();
  for (let i = 0; i < upTo; i++) apply(s, events[i]);
  return s;
}

export function apply(s: RunState, e: RunEvent): void {
  s.lastTs = Math.max(s.lastTs, e.ts);
  const r = e.round;
  switch (e.kind) {
    case "run":
      s.runId = e.data.run_id;
      s.startTs = e.ts;
      return;
    case "world":
      s.world = e.data.theta;
      return;
    case "submission": {
      if (r == null) return;
      round(s, r).attempts.push({ attempt: e.data.attempt, ts: e.ts, scene: e.data.scene, device: e.data.device });
      s.phase = { kind: "certifying", round: r, attempt: e.data.attempt };
      return;
    }
    case "certificate": {
      if (r == null) return;
      const a = round(s, r).attempts.find((x) => x.attempt === e.data.attempt);
      if (a) a.cert = { ts: e.ts, passed: e.data.passed, verdicts: e.data.verdicts, seconds: e.data.seconds };
      if (!e.data.passed) s.phase = { kind: "rejected", round: r, attempt: e.data.attempt };
      return;
    }
    case "instances":
      if (r != null) round(s, r).instances = { A: e.data.A, B: e.data.B };
      return;
    case "card": {
      if (r == null) return;
      const rs = round(s, r);
      rs.card = e.data.card;
      rs.version = e.data.card.version;
      rs.cardTs = e.ts;
      return;
    }
    case "channel":
      s.channel.push({
        ts: e.ts,
        seq: e.data.seq,
        route: e.data.route,
        channel: e.data.channel,
        kind: e.data.kind,
        hash: e.data.hash,
        summary: e.data.summary,
      });
      return;
    case "report":
      if (r == null) return;
      round(s, r).report = e.data.report;
      round(s, r).reportTs = e.ts;
      s.phase = { kind: "reported", round: r };
      return;
    case "session_end": {
      if (r == null || !e.label) return;
      const ss = session(s, r, e.label);
      ss.tickets = e.data.tickets ?? [];
      ss.endTs = ss.endTs ?? e.ts;
      ss.step = "done";
      return;
    }
    case "agent_start":
      if (e.agent === "builder") {
        s.builder = { ...s.builder, session: e.data.session, model: e.data.model, active: true, since: e.ts };
        if (r != null) {
          round(s, r).builderSessions.push({ session: e.data.session, startTs: e.ts });
          s.phase = { kind: "building", round: r };
        }
      } else if (e.agent === "learner" && r != null && e.label) {
        s.learner = { ...s.learner, session: e.data.session, model: e.data.model, active: true, since: e.ts, label: e.label, round: r };
        const ss = session(s, r, e.label);
        ss.tag = e.data.session;
        ss.model = e.data.model;
        ss.startTs = e.ts;
        learnerPhase(s, r, e.label, "pretest");
      }
      return;
    case "agent_end":
      if (e.agent === "builder") {
        s.builder = { ...s.builder, active: false };
        const b = r != null ? round(s, r).builderSessions.find((x) => x.session === e.data.session) : undefined;
        if (b) b.endTs = e.ts;
      } else if (e.agent === "learner") {
        s.learner = { ...s.learner, active: false };
        if (r != null && e.label) session(s, r, e.label).endTs = e.ts;
      }
      return;
    case "thought": {
      const track = e.agent === "builder" ? s.builder : s.learner;
      track.thought = { ts: e.ts, value: e.data.text };
      if (e.agent === "learner" && r != null && e.label) session(s, r, e.label).thoughts += 1;
      return;
    }
    case "say":
      if (e.agent === "builder") {
        s.builder.say = { ts: e.ts, value: e.data.text };
        if (r != null) round(s, r).says.push({ ts: e.ts, value: e.data.text });
      } else s.learner.say = { ts: e.ts, value: e.data.text };
      return;
    case "tool": {
      const track = e.agent === "builder" ? s.builder : s.learner;
      track.tool = { ts: e.ts, value: { tool: e.data.tool, command: e.data.command, ok: e.data.ok } };
      if (e.agent === "learner" && r != null && e.label) {
        session(s, r, e.label).toolCalls.push({ ts: e.ts, tool: e.data.tool, command: e.data.command });
        if (/\.\/lab finish-lab/.test(e.data.command)) learnerPhase(s, r, e.label, "theory");
      }
      return;
    }
    case "check":
      if (r != null) round(s, r).checks.push({ ts: e.ts, result: e.data.result, verdicts: e.data.verdicts, detail: e.data.detail });
      return;
    case "goal": {
      if (r == null || !e.label) return;
      const ss = session(s, r, e.label);
      ss.goals[e.data.phase][e.data.index] = e.data.goal;
      learnerPhase(s, r, e.label, e.data.phase);
      return;
    }
    case "answer": {
      if (r == null || !e.label) return;
      const ss = session(s, r, e.label);
      ss.answers.push({
        ts: e.ts,
        phase: e.data.phase,
        index: e.data.index,
        knobs: e.data.knobs,
        goal: ss.goals[e.data.phase][e.data.index] ?? null,
      });
      learnerPhase(s, r, e.label, e.data.phase);
      return;
    }
    case "theory":
      if (r == null || !e.label) return;
      session(s, r, e.label).theory = { ts: e.ts, value: { code: e.data.code, belief: e.data.belief } };
      learnerPhase(s, r, e.label, "exam");
      return;
    case "experiment": {
      if (r == null || !e.label) return;
      const ss = session(s, r, e.label);
      ss.experiments.push({ ...e.data, ts: e.ts });
      learnerPhase(s, r, e.label, "lab");
      return;
    }
    case "results":
      if (r == null || !e.label) return;
      session(s, r, e.label).results = { ts: e.ts, value: { pretest: e.data.pretest, exam: e.data.exam } };
      learnerPhase(s, r, e.label, "report");
      return;
    case "session_final":
      if (r == null || !e.label) return;
      session(s, r, e.label).final = e.data;
      return;
    case "note":
      if (r == null || !e.label) return;
      session(s, r, e.label).notes.push({ ts: e.ts, value: e.data.text });
      return;
    case "run_end":
      s.end = e.data;
      s.phase = { kind: "ended" };
      return;
    case "audit":
      s.audit = { clean: e.data.clean, hits: e.data.hits, viewer_tokens: e.data.viewer_tokens };
      return;
    default:
      assertNever(e);
  }
}

/** Index of the first event later than `ts` (events sorted by time). */
export function upperBound(events: RunEvent[], ts: number): number {
  let lo = 0;
  let hi = events.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (events[mid].ts <= ts) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function sortEvents(events: RunEvent[]): RunEvent[] {
  return [...events].sort((a, b) => a.ts - b.ts || a.seq - b.seq);
}
