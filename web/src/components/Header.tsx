import { elapsed, modelShort } from "../data/derive";
import { openSource } from "../data/source";
import { toReal } from "../data/timeline";
import { assertNever } from "../data/types";
import { useCursorState, useFullState } from "../state/runState";
import { useStore, type View } from "../state/store";

const VIEWS: { id: View; name: string }[] = [
  { id: "stage", name: "舞台" },
  { id: "learning", name: "学习过程" },
  { id: "accumulation", name: "跨轮积累" },
  { id: "conclusion", name: "结论" },
];

const SPEEDS = [1, 10, 30, 100];

export function Header() {
  const runs = useStore((s) => s.runs);
  const listing = useStore((s) => s.listing);
  const source = useStore((s) => s.source);
  const status = useStore((s) => s.status);
  const playing = useStore((s) => s.playing);
  const speed = useStore((s) => s.speed);
  const follow = useStore((s) => s.follow);
  const god = useStore((s) => s.god);
  const view = useStore((s) => s.view);
  const token = useStore((s) => s.token);
  const tour = useStore((s) => s.tour);
  const realNow = useStore((s) => toReal(s.timeline, s.disp));
  const full = useFullState();
  const cursor = useCursorState();
  const store = useStore.getState;

  const start = full.startTs || realNow;
  const total = Math.max(0, full.lastTs - start);
  const at = Math.max(0, realNow - start);
  const live = source?.live ?? false;
  const builderModel = full.builder.model ?? full.end?.builder;
  const learnerModel = full.learner.model ?? full.end?.learner;

  const choose = (key: string) => {
    const next = runs.find((r) => `${r.source}:${r.run_id}` === key);
    if (next) store().open(next, openSource(next, token));
  };

  return (
    <header className="header">
      <div className="brand">
        <span className="brand-mark" aria-hidden>
          ◎
        </span>
        <span className="brand-name">观察窗</span>
        <span className="label">AI_Physist</span>
      </div>

      <label className="run-picker">
        <span className="label">运行</span>
        <select value={listing ? `${listing.source}:${listing.run_id}` : ""} onChange={(e) => choose(e.target.value)}>
          {(["live", "recorded"] as const).map((src) => {
            const group = runs.filter((r) => r.source === src);
            if (!group.length) return null;
            return (
              <optgroup key={src} label={src === "live" ? "本机运行（直播服务）" : "已录制演示"}>
                {group.map((r) => (
                  <option key={`${r.source}:${r.run_id}`} value={`${r.source}:${r.run_id}`}>
                    {r.run_id}
                    {r.live ? " · 进行中" : ""}
                    {r.rerun_of ? ` · ${r.rerun_of} 的对照` : ""}
                  </option>
                ))}
              </optgroup>
            );
          })}
        </select>
      </label>

      <div className="models mono" title="建造者 / 学习者">
        <span>B {modelShort(builderModel)}</span>
        <span>L {modelShort(learnerModel)}</span>
      </div>

      <div className="transport">
        {live ? (
          <span className={`live-badge ${status === "open" ? "on" : ""}`}>
            <i aria-hidden /> {status === "open" ? "直播" : status === "connecting" ? "连接中" : "已断开"}
          </span>
        ) : (
          <span className="label">回放</span>
        )}
        <button className="btn" onClick={() => store().seekDisp(0)} title="回到开头">
          ⏮
        </button>
        <button className="btn play" onClick={() => store().setPlaying(!playing)} aria-pressed={false}>
          {playing ? "❚❚ 暂停" : "▶ 播放"}
        </button>
        <div className="seg" role="group" aria-label="播放速度">
          {SPEEDS.map((x) => (
            <button key={x} aria-pressed={speed === x} onClick={() => store().setSpeed(x)}>
              {x}×
            </button>
          ))}
        </div>
        {live && (
          <button className="btn" aria-pressed={follow} onClick={() => store().setFollow(!follow)}>
            {follow ? "跟随直播中" : "回到直播"}
          </button>
        )}
        <span className="clock mono">
          {elapsed(at)} <span className="muted">/ {elapsed(total)}</span>
        </span>
        {cursor.phase.kind !== "idle" && <PhaseText />}
      </div>

      <nav className="seg views" aria-label="视图">
        {VIEWS.map((v) => (
          <button key={v.id} aria-pressed={view === v.id} onClick={() => store().setView(v.id)}>
            {v.name}
          </button>
        ))}
      </nav>
      <button className="btn" aria-pressed={god} onClick={() => store().setGod(!god)} title="显示隐藏真值（学习者看不到）">
        上帝视角
      </button>
      <button className="btn" aria-pressed={false} onClick={() => store().setTour({ on: !tour.on, step: tour.on ? tour.step : 0 })}>
        {tour.on ? "退出导览" : "导览"}
      </button>
    </header>
  );
}

function PhaseText() {
  const s = useCursorState();
  const p = s.phase;
  let text = "";
  switch (p.kind) {
    case "building":
      text = `第 ${p.round} 轮 · 建造中`;
      break;
    case "certifying":
      text = `第 ${p.round} 轮 · 认证第 ${p.attempt} 次提交`;
      break;
    case "rejected":
      text = `第 ${p.round} 轮 · 第 ${p.attempt} 次提交被退回`;
      break;
    case "learning":
      text = `第 ${p.round} 轮 · 实例 ${p.label} · ${STEP_NAME[p.step]}`;
      break;
    case "reported":
      text = `第 ${p.round} 轮 · 成绩单已发给建造者`;
      break;
    case "ended":
      text = "运行结束";
      break;
    case "idle":
      text = "";
      break;
    default:
      assertNever(p);
  }
  return <span className="phase-text">{text}</span>;
}

export const STEP_NAME = {
  pretest: "前测",
  lab: "实验",
  theory: "提交理论",
  exam: "考试",
  report: "反馈",
  done: "完成",
} as const;
