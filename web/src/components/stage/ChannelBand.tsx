import type { ChannelEntry } from "../../data/fold";
import { useCursorState, useFullState } from "../../state/runState";

type Zone = "builder" | "referee" | "learner";

const ROUTE: Record<string, { to: Zone; arrow: string }> = {
  "builder->referee": { to: "referee", arrow: "→" },
  "referee->builder": { to: "builder", arrow: "←" },
  "referee->learner": { to: "learner", arrow: "→" },
  "builder->learner (via referee)": { to: "learner", arrow: "→" },
  "learner->referee": { to: "referee", arrow: "←" },
};

function describe(e: ChannelEntry): string {
  const s = e.summary as Record<string, unknown>;
  switch (e.kind) {
    case "submission":
      return `提交 第${s.round}轮#${s.attempt} ${s.device ?? ""}`;
    case "rejection":
      return `退回 第${s.round}轮#${s.attempt}`;
    case "task_card":
      return `任务卡 v${s.version}`;
    case "session_summary":
      return `会话摘要 实例${s.instance} · ${s.experiments} 次实验`;
    case "round_report":
      return `成绩单 第${s.round}轮`;
    default:
      return e.kind;
  }
}

function Packet({ e }: { e: ChannelEntry }) {
  const r = ROUTE[e.route] ?? { to: "referee", arrow: "·" };
  return (
    <span key={e.seq} className={`packet from-${r.arrow === "→" ? "left" : "right"}`}>
      <span className="mono">{r.arrow}</span> {describe(e)}
    </span>
  );
}

/** Every message that crosses an agent boundary passes the referee and enters a hash chain. */
export function ChannelBand() {
  const s = useCursorState();
  const full = useFullState();
  const latest = (zone: Zone) => [...s.channel].reverse().find((e) => (ROUTE[e.route]?.to ?? "referee") === zone);
  const chain = s.channel.slice(-7);
  const audit = full.end?.isolation_audit;
  return (
    <section className="channel">
      <div className="zone">
        <span className="label">建造者区</span>
        {latest("builder") && <Packet e={latest("builder")!} />}
      </div>
      <div className="wall" aria-label="沙箱边界">
        <span>沙箱边界</span>
      </div>
      <div className="zone mid">
        <span className="label">裁判 · 信道</span>
        {latest("referee") && <Packet e={latest("referee")!} />}
        <ol className="chain mono" aria-label="哈希链">
          {chain.map((e) => (
            <li key={e.seq} title={`${e.route} ${e.kind}\n${e.hash}`}>
              #{e.seq} <span className="muted">{e.hash.slice(0, 6)}</span>
            </li>
          ))}
        </ol>
        {audit && (
          <span className={`tag ${audit.clean ? "pass" : "fail"}`}>
            canary 审计 {audit.clean ? "无泄漏" : "发现泄漏"} · 链 {full.end?.chain_ok ? "完整" : "损坏"} {full.end?.chain_entries} 条
          </span>
        )}
      </div>
      <div className="wall" aria-label="沙箱边界">
        <span>沙箱边界</span>
      </div>
      <div className="zone">
        <span className="label">学习者区</span>
        {latest("learner") && <Packet e={latest("learner")!} />}
      </div>
    </section>
  );
}
