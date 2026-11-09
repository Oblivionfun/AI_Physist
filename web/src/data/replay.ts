import type { Replay, Scene } from "./types";

export interface DecodedReplay {
  fps: number;
  parts: string[];
  frames: number;
  /** frames x parts x [px, py, pz, qx, qy, qz, qw] */
  data: Float32Array;
  outcome: number[] | null;
  status: string;
  tOutcome: number;
}

const cache = new WeakMap<Replay, DecodedReplay>();

export function decodeReplay(rep: Replay): DecodedReplay {
  const hit = cache.get(rep);
  if (hit) return hit;
  const bin = atob(rep.data);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const raw = new Int16Array(bytes.buffer);
  const data = new Float32Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    data[i] = i % 7 < 3 ? raw[i] / rep.pos_scale : raw[i] / 32767;
  }
  const out: DecodedReplay = {
    fps: rep.fps,
    parts: rep.parts,
    frames: rep.frames,
    data,
    outcome: rep.outcome,
    status: rep.status,
    tOutcome: rep.t_outcome,
  };
  cache.set(rep, out);
  return out;
}

const AXIS: Record<string, number> = { x: 0, y: 1, z: 2 };

/** World point of an outcome (or goal) value, on the floor for landing tasks. */
export function outcomePoint(scene: Scene, value: number[] | null | undefined): [number, number, number] | null {
  if (!value) return null;
  const { kind, axes, base } = scene.outcome;
  if (kind !== "landing_point" && kind !== "final_position") return null;
  const p: [number, number, number] = [base[0], base[1], kind === "landing_point" ? 0 : base[2]];
  axes.forEach((a, i) => {
    p[AXIS[a]] = value[i];
  });
  if (kind === "landing_point") p[2] = 0.002;
  return p;
}
