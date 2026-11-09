import { useEffect, useState } from "react";
import { fold, sortEvents } from "../data/fold";
import { roundMetrics, type RoundMetrics } from "../data/metrics";
import { BundleSource } from "../data/source";
import type { RunEvent, RunListing } from "../data/types";
import { useStore } from "./store";

export interface RelatedRun {
  run_id: string;
  learner?: string | null;
  role: string;
  metrics: RoundMetrics[];
}

function role(id: string, base: string): string {
  if (id === base) return "正式运行";
  if (id.includes("amnesic")) return "每次清空笔记";
  if (id.includes("weak")) return "较弱模型";
  if (id.includes("scripted")) return "黑盒脚本学习者";
  return "对照";
}

/** Runs that share the certified devices of the current one (`mlab rerun-learner`). */
export function useRelatedRuns(current?: RunListing): RelatedRun[] {
  const runs = useStore((s) => s.runs);
  const token = useStore((s) => s.token);
  const [out, setOut] = useState<RelatedRun[]>([]);
  useEffect(() => {
    setOut([]);
    if (!current) return;
    const base = current.rerun_of ?? current.run_id;
    const family = runs.filter((r) => r.source === "recorded" && (r.run_id === base || r.rerun_of === base));
    if (family.length < 2) return;
    let alive = true;
    Promise.all(
      family.map(
        (r) =>
          new Promise<RelatedRun>((resolve) => {
            const src = new BundleSource(r.run_id, `recorded/${r.path ?? `${r.run_id}/viz`}`, token);
            src.subscribe((events: RunEvent[]) =>
              resolve({ run_id: r.run_id, learner: r.learner, role: role(r.run_id, base), metrics: roundMetrics(fold(sortEvents(events))) }),
            );
          }),
      ),
    ).then((x) => {
      if (alive) setOut(x);
    });
    return () => {
      alive = false;
    };
  }, [current, runs, token]);
  return out;
}
