import type { Curves, Label, Replay, RunEvent, RunListing } from "./types";

/**
 * Two ways to get a run: a static bundle exported by `observatory export` (works from any
 * file server), or the token-gated live server (`observatory serve`), which also streams.
 */
export interface RunSource {
  readonly runId: string;
  readonly live: boolean;
  /** Delivers the backlog, then (live only) new events as they arrive. Returns a stop function. */
  subscribe(onEvents: (events: RunEvent[]) => void, onStatus?: (s: StreamStatus) => void): () => void;
  sessionReplays(round: number, label: Label): Promise<Record<string, Replay>>;
  replay(round: number, label: Label, kind: string, index: number): Promise<Replay | null>;
  curves(round: number, knob?: string): Promise<Curves | null>;
}

export type StreamStatus = "connecting" | "open" | "closed" | "error";

const TOKEN_KEY = "observatory-token";

/** The live server prints a URL with #token=...; keep it for this tab only and hide it. */
export function readToken(): string | null {
  const m = /token=([^&]+)/.exec(window.location.hash);
  if (m) {
    sessionStorage.setItem(TOKEN_KEY, decodeURIComponent(m[1]));
    history.replaceState(null, "", window.location.pathname + window.location.search);
  }
  return sessionStorage.getItem(TOKEN_KEY);
}

function withToken(url: string, token: string | null): string {
  if (!token) return url;
  return url + (url.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(token);
}

async function getJson<T>(url: string, token: string | null): Promise<T> {
  const res = await fetch(withToken(url, token), { cache: "no-store" });
  if (!res.ok) throw new Error(`${res.status} ${url}`);
  return (await res.json()) as T;
}

export async function listRuns(token: string | null): Promise<RunListing[]> {
  const out: RunListing[] = [];
  if (token) {
    try {
      const r = await getJson<{ runs: { run_id: string; live: boolean; ended: boolean }[] }>("api/runs", token);
      for (const x of r.runs) out.push({ run_id: x.run_id, source: "live", live: x.live, ended: x.ended });
    } catch {
      /* no live server: recorded bundles only */
    }
  }
  try {
    const idx = await getJson<{ runs: Omit<RunListing, "source">[] }>("recorded/viz-index.json", token);
    for (const x of idx.runs) out.push({ ...x, source: "recorded" });
  } catch {
    /* no bundles exported yet */
  }
  return out;
}

interface Manifest {
  run_id: string;
  events: string;
  replays: Record<string, string>;
  curves: Record<string, Record<string, string>>;
}

export class BundleSource implements RunSource {
  readonly live = false;
  private manifest: Promise<Manifest>;
  private replayCache = new Map<string, Promise<Record<string, Replay>>>();

  constructor(
    readonly runId: string,
    private base: string,
    private token: string | null,
  ) {
    this.manifest = getJson<Manifest>(`${base}/manifest.json`, token);
  }

  subscribe(onEvents: (events: RunEvent[]) => void, onStatus?: (s: StreamStatus) => void) {
    let stopped = false;
    onStatus?.("connecting");
    this.manifest
      .then((m) => getJson<RunEvent[]>(`${this.base}/${m.events}`, this.token))
      .then((events) => {
        if (stopped) return;
        onEvents(events);
        onStatus?.("closed");
      })
      .catch(() => onStatus?.("error"));
    return () => {
      stopped = true;
    };
  }

  sessionReplays(round: number, label: Label) {
    const key = `${round}:${label}`;
    let p = this.replayCache.get(key);
    if (!p) {
      p = this.manifest.then((m) =>
        m.replays[key] ? getJson<Record<string, Replay>>(`${this.base}/${m.replays[key]}`, this.token) : {},
      );
      this.replayCache.set(key, p);
    }
    return p;
  }

  async replay(round: number, label: Label, kind: string, index: number) {
    const all = await this.sessionReplays(round, label);
    return all[`${kind}:${index}`] ?? null;
  }

  async curves(round: number, knob?: string) {
    const m = await this.manifest;
    const entry = m.curves[String(round)];
    if (!entry) return null;
    const rel = entry[knob ?? entry.default] ?? entry[entry.default];
    return rel ? getJson<Curves>(`${this.base}/${rel}`, this.token) : null;
  }
}

export class LiveSource implements RunSource {
  readonly live = true;
  private replayCache = new Map<string, Promise<Replay | null>>();

  constructor(
    readonly runId: string,
    private token: string,
  ) {}

  private api(path: string) {
    return `api/runs/${encodeURIComponent(this.runId)}/${path}`;
  }

  subscribe(onEvents: (events: RunEvent[]) => void, onStatus?: (s: StreamStatus) => void) {
    let last = -1;
    let es: EventSource | null = null;
    let stopped = false;
    let retry: number | undefined;
    const open = () => {
      if (stopped) return;
      onStatus?.("connecting");
      es = new EventSource(withToken(this.api(`stream?after=${last}`), this.token));
      es.onopen = () => onStatus?.("open");
      es.addEventListener("batch", (msg) => {
        const batch = JSON.parse((msg as MessageEvent).data) as RunEvent[];
        if (batch.length) last = batch[batch.length - 1].seq;
        onEvents(batch);
      });
      es.onerror = () => {
        onStatus?.("error");
        es?.close();
        retry = window.setTimeout(open, 3000);
      };
    };
    open();
    return () => {
      stopped = true;
      window.clearTimeout(retry);
      es?.close();
      onStatus?.("closed");
    };
  }

  sessionReplays(round: number, label: Label) {
    return getJson<Record<string, Replay>>(this.api(`replays?round=${round}&label=${label}`), this.token);
  }

  replay(round: number, label: Label, kind: string, index: number) {
    const key = `${round}:${label}:${kind}:${index}`;
    let p = this.replayCache.get(key);
    if (!p) {
      p = getJson<Replay>(this.api(`replay?round=${round}&label=${label}&kind=${kind}&index=${index}`), this.token).catch(
        () => {
          this.replayCache.delete(key);
          return null;
        },
      );
      this.replayCache.set(key, p);
    }
    return p;
  }

  async curves(round: number, knob?: string): Promise<Curves | null> {
    const q = `curves?round=${round}` + (knob ? `&knob=${encodeURIComponent(knob)}` : "");
    for (let i = 0; i < 60; i++) {
      const res = await fetch(withToken(this.api(q), this.token), { cache: "no-store" });
      if (res.status === 200) return (await res.json()) as Curves;
      if (res.status !== 202) return null;
      await new Promise((r) => setTimeout(r, 1500));
    }
    return null;
  }
}

export function openSource(listing: RunListing, token: string | null): RunSource {
  if (listing.source === "live" && token) return new LiveSource(listing.run_id, token);
  return new BundleSource(listing.run_id, `recorded/${listing.path ?? `${listing.run_id}/viz`}`, token);
}
