import { useMemo, useState } from "react";
import { expRows, fmt, knobText, predictionError, tolerance, trueOutcomes } from "../../data/derive";
import { useCursorState, useReplay } from "../../state/runState";
import { useStore } from "../../state/store";
import { STEP_NAME } from "../Header";
import { DeviceScene, type CameraMode, type Marks } from "../three/DeviceScene";
import { stageFocus } from "./focus";
import { GateStrip } from "./GateStrip";

const CAMERAS: { id: CameraMode; name: string }[] = [
  { id: "three", name: "三分之四" },
  { id: "side", name: "侧视" },
  { id: "follow", name: "跟随球" },
];

export function CenterStage() {
  const s = useCursorState();
  const god = useStore((x) => x.god);
  const speed = useStore((x) => x.speed);
  const playing = useStore((x) => x.playing);
  const [camera, setCamera] = useState<CameraMode>("three");
  const f = useMemo(() => stageFocus(s), [s]);
  const action = f.action;
  const tol = f.scene?.tolerance ?? tolerance(f.rs);

  const kind = action?.kind;
  const index = action ? (action.kind === "lab" ? action.exp.index : action.answer.index) : undefined;
  const replay = useReplay(f.candidate ? undefined : f.round, f.label, kind, index);

  const marks: Marks = useMemo(() => {
    if (!f.ss || !action) return {};
    if (action.kind === "lab") {
      const rows = expRows(f.ss, tol);
      const past = rows.filter((r) => r.exp.index < action.exp.index && r.exp.outcome).map((r) => ({ value: r.exp.outcome!, faint: true }));
      const truth = trueOutcomes(f.ss).get(action.exp.index)?.true_outcome ?? replay?.outcome ?? null;
      return { past, prediction: action.exp.prediction, observed: action.exp.outcome, truth: god ? truth : null };
    }
    const a = action.answer;
    const revealed = f.ss.results?.value[a.phase]?.[a.index];
    const observed = revealed?.observed_outcome ?? replay?.outcome ?? null;
    const err = a.goal && observed ? predictionError(a.goal, observed, tol).err : null;
    const verdict = revealed ? (revealed.success ? "hit" : "miss") : err != null ? (err <= 1 ? "hit" : "miss") : null;
    const past = f.ss.answers
      .filter((x) => x.phase === a.phase && x.index < a.index)
      .map((x) => f.ss!.results?.value[x.phase]?.[x.index]?.observed_outcome)
      .filter((v): v is number[] => !!v)
      .map((value) => ({ value, faint: true }));
    return { goal: a.goal, observed, verdict, past, truth: god ? replay?.outcome ?? null : null };
  }, [f, action, replay, god, tol]);

  const latestAttempt = f.rs?.attempts.at(-1);
  const showGates = s.phase.kind === "certifying" || s.phase.kind === "rejected" || (s.phase.kind === "building" && latestAttempt);
  const rate = playing ? (speed >= 100 ? 4 : speed >= 30 ? 2.5 : speed >= 10 ? 1.6 : 1) : 1;
  const hiddenLabels = useMemo(() => {
    if (!god || !f.scene || !f.rs?.instances || !f.label) return undefined;
    const theta = f.rs.instances[f.label];
    const out: Record<string, string> = {};
    for (const part of f.scene.parts) {
      const name = part.hidden_mass;
      if (name && theta[name] != null) out[part.name] = `${name} = ${theta[name].toFixed(3)} kg`;
    }
    return out;
  }, [god, f]);

  return (
    <section className="center">
      {f.scene ? (
        <div className="canvas-wrap">
          <DeviceScene
            scene={f.scene}
            replay={replay}
            replayKey={`${f.round}:${f.label}:${kind}:${index}`}
            rate={rate}
            marks={marks}
            camera={camera}
            partLabels={hiddenLabels}
          />
        </div>
      ) : (
        <div className="canvas-wrap empty">
          <p className="label">等待建造者的第一次提交</p>
        </div>
      )}

      <div className="stage-head">
        <p className="label">
          <b>02</b> 裁判 · 3D 舞台 {f.scene && <span className="mono">· {f.scene.name}</span>}
          {f.candidate && <span className="tag">候选设计</span>}
          {s.phase.kind === "building" && !f.rs?.attempts.length && f.scene && <span className="tag">上一轮已认证的装置</span>}
        </p>
        <ActionLine />
      </div>

      {showGates && <GateStrip attempt={latestAttempt} pending={!latestAttempt?.cert} />}

      <div className="stage-foot">
        <div className="legend">
          <span>
            <i className="lg ring" /> 学习者的预测（环半径 = 容差 {fmt(tol, 3)} m）
          </span>
          <span>
            <i className="lg dot" /> 观测落点
          </span>
          <span>
            <i className="lg goal" /> 考试目标
          </span>
          {god && (
            <span className="truth">
              <i className="lg cross" /> 真值（无噪声）
            </span>
          )}
          <span className="muted">回放为无执行噪声的意图重演</span>
        </div>
        <div className="seg" role="group" aria-label="机位">
          {CAMERAS.map((c) => (
            <button key={c.id} aria-pressed={camera === c.id} onClick={() => setCamera(c.id)}>
              {c.name}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function ActionLine() {
  const s = useCursorState();
  const f = stageFocus(s);
  const tol = tolerance(f.rs);
  if (!f.ss || !f.action || s.phase.kind !== "learning") {
    if (s.phase.kind === "reported" && f.rs?.report) {
      const ins = f.rs.report.instances;
      return (
        <p className="action-line">
          成绩单：考试 {ins.map((x) => `${x.label} ${Math.round(x.exam_success * 100)}%`).join(" · ")}，黑盒对照{" "}
          {Math.round((f.rs.report.controls.blackbox_exam_success ?? 0) * 100)}%
        </p>
      );
    }
    return null;
  }
  const step = STEP_NAME[f.ss.step];
  if (f.action.kind === "lab") {
    const e = f.action.exp;
    const { err, kind } = predictionError(e.prediction, e.outcome, tol);
    return (
      <p className="action-line">
        <span className="tag">实例 {f.label}</span> {step} #{e.index + 1}
        {e.probe && <span className="tag">裁判探针</span>}
        <span className="mono"> {knobText(e.knobs)}</span>
        <span className="signal mono"> 预测 {e.prediction ? fmt(e.prediction[0]) : "无落点"}</span>
        <span className="mono"> 观测 {e.outcome ? fmt(e.outcome[0]) : "无落点"}</span>
        <span className={`mono ${err != null && err <= 1 ? "hit" : ""}`}>
          {" "}
          Δ {kind === "value" ? `${fmt(err, 2)} 容差` : kind === "null-right" ? "预测正确（无落点）" : "预测与结果类型不符"}
        </span>
      </p>
    );
  }
  const a = f.action.answer;
  const revealed = f.ss.results?.value[a.phase]?.[a.index];
  return (
    <p className="action-line">
      <span className="tag">实例 {f.label}</span> {a.phase === "pretest" ? "前测" : "考试"} 第 {a.index + 1} 题
      <span className="mono"> 目标 {a.goal ? fmt(a.goal[0]) : "—"}</span>
      <span className="mono"> {knobText(a.knobs)}</span>
      {revealed ? (
        <span className={`tag ${revealed.success ? "hit" : "miss"}`}>{revealed.success ? "命中" : "未命中"}</span>
      ) : (
        <span className="muted"> 结果在会话结束后公布</span>
      )}
    </p>
  );
}
