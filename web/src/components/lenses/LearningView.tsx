import { deviation } from "d3-array";
import { useMemo, useState } from "react";
import { certifiedScene, examScore, expRows, fmt, median, pct, roundsOf, tolerance } from "../../data/derive";
import type { SessionState } from "../../data/fold";
import type { Knob, Label } from "../../data/types";
import { useCurves, useFullState, useReplay } from "../../state/runState";
import { useStore } from "../../state/store";
import { BeliefForest } from "../charts/BeliefForest";
import { ErrorSpark } from "../charts/ErrorSpark";
import { ExamStrip } from "../charts/ExamStrip";
import { KnobPath } from "../charts/KnobPath";
import { PredObs } from "../charts/PredObs";
import { ResponseSlice } from "../charts/ResponseSlice";
import { Rhythm } from "../charts/Rhythm";
import { Traces } from "../charts/Traces";
import { useSize } from "../charts/useSize";
import { DeviceScene } from "../three/DeviceScene";
import { Panel } from "./Panel";

export function LearningView() {
  const s = useFullState();
  const god = useStore((x) => x.god);
  const focus = useStore((x) => x.focus);
  const setFocus = useStore((x) => x.setFocus);
  const rounds = roundsOf(s).filter((r) => r.sessions.A || r.sessions.B);
  const round = focus.round ?? rounds.at(-1)?.round;
  const rs = rounds.find((r) => r.round === round);
  const label: Label = focus.label ?? "A";
  const ss = rs?.sessions[label];
  const tol = tolerance(rs);
  const rows = useMemo(() => expRows(ss, tol), [ss, tol]);
  const sel = focus.exp ?? rows.at(-1)?.exp.index;
  const selExp = ss?.experiments.find((e) => e.index === sel);
  const card = rs?.card;
  const scene = certifiedScene(rs);
  const report = rs?.report?.instances.find((x) => x.label === label);
  const [knob, setKnob] = useState<string | undefined>();
  const [modKey, setModKey] = useState<string | null>(null);
  const [modIdx, setModIdx] = useState(0);
  const controller = useMemo(() => controllerKnob(ss, card?.knobs), [ss, card]);
  const curves = useCurves(round, knob ?? controller, `${ss?.final ? 1 : 0}${ss?.theory ? 1 : 0}${ss?.answers.length ?? 0}`);
  const replay = useReplay(round, label, "lab", sel);
  const [rightRef, rightSize] = useSize<HTMLDivElement>();
  const [rhythmRef, rhythmSize] = useSize<HTMLDivElement>({ width: 900, height: 70 });

  if (!rs || !ss || !card || !scene) {
    return (
      <div className="view-pad">
        <p className="label">还没有学习会话</p>
        <p className="muted">建造者的设计通过认证后，学习者的会话会出现在这里。</p>
      </div>
    );
  }

  const third = Math.max(1, Math.floor(rows.length / 3));
  const first = median(rows.slice(0, third).map((r) => r.err ?? NaN));
  const last = median(rows.slice(-third).map((r) => r.err ?? NaN));
  const within = rows.filter((r) => r.err != null && r.err <= 1).length;
  const pre = examScore(ss, "pretest");
  const exam = examScore(ss, "exam");
  const select = (i: number) => setFocus({ round, label, exp: i });
  const goal = card.outcome.goal_space[0];
  const ranges = Object.fromEntries(card.knobs.map((k) => [k.name, k.high - k.low]));

  const c = curves === "loading" ? null : curves;
  const modKeys = c ? [...new Set(c.variants.filter((v) => v.key).map((v) => v.key as string))] : [];
  const activeKey = modKey && modKeys.includes(modKey) ? modKey : null;
  const modVariants = c && activeKey ? c.variants.filter((v) => v.key === activeKey) : [];
  const variant = c ? (activeKey ? (modVariants[Math.min(modIdx, modVariants.length - 1)] ?? c.variants[0]) : c.variants[0]) : null;
  const hitRates = report?.theory_hit_rates ?? {};
  const modRate = activeKey ? Object.entries(hitRates).find(([k]) => k.includes(activeKey))?.[1] : null;

  return (
    <div className="learning">
      <div className="lens-bar">
        <span className="label">
          <b>学习过程</b>
        </span>
        <div className="seg">
          {rounds.map((r) => (
            <button key={r.round} aria-pressed={r.round === round} onClick={() => setFocus({ round: r.round, label })}>
              第 {r.round} 轮
            </button>
          ))}
        </div>
        <div className="seg">
          {(["A", "B"] as Label[]).map((l) => (
            <button key={l} aria-pressed={l === label} disabled={!rs.sessions[l]} onClick={() => setFocus({ round, label: l })}>
              实例 {l}
            </button>
          ))}
        </div>
        <span className="mono muted">
          {scene.name} v{rs.version} · 预算 {card.protocol.budget} · 容差 {tol} m
        </span>
        {!god && <span className="tag truth">打开上帝视角可看真值曲线、真值参数</span>}
      </div>

      <div className="lens-grid">
        <Panel
          idx="01"
          title="先预测，再观测"
          className="a"
          note={
            <>
              {rows.length} 次实验，{within} 次预测落在容差内（{pct(rows.length ? within / rows.length : null)}）。越靠近对角线越准，颜色越深越晚。
            </>
          }
        >
          <PredObs rows={rows} tol={tol} goal={goal} selected={sel} onSelect={select} />
        </Panel>

        <Panel
          idx="02"
          title="预测误差随实验下降"
          className="b"
          note={
            <>
              前 1/3 中位 <b className="mono">{fmt(first, 2)}×</b> → 后 1/3 中位{" "}
              <b className={`mono ${last != null && first != null && last < first ? "hit" : "miss"}`}>{fmt(last, 2)}×</b> 容差。菱形是裁判指定动作的探针（不由学习者挑选）。
            </>
          }
        >
          <ErrorSparkWide rows={rows} budget={card.protocol.budget} selected={sel} onSelect={select} />
        </Panel>

        <Panel idx="05" title="它相信什么：信念 vs 真值" className="e" note="橙色是学习者自报的 90% 区间，蓝线是真值；右列是单位误差（误差 / 先验宽度）。">
          <div ref={rightRef} className="fill">
            <BeliefForest
              unknowns={card.unknowns}
              belief={ss.final?.belief ?? ss.theory?.value.belief}
              truth={rs.instances?.[label] ?? s.world}
              god={god}
              width={Math.max(280, rightSize.width)}
            />
          </div>
        </Panel>

        <Panel
          idx="03"
          title="它的理论 vs 真实物理"
          className="c"
          tools={
            c && (
              <div className="tools">
                <div className="seg">
                  {c.knobs.map((k) => (
                    <button key={k} aria-pressed={k === c.knob} onClick={() => setKnob(k)}>
                      {k}
                    </button>
                  ))}
                </div>
                <div className="seg">
                  <button aria-pressed={!activeKey} onClick={() => setModKey(null)}>
                    原装置
                  </button>
                  {modKeys.map((k) => (
                    <button
                      key={k}
                      aria-pressed={k === activeKey}
                      onClick={() => {
                        setModKey(k);
                        setModIdx(Math.max(0, c.variants.filter((v) => v.key === k).findIndex((v) => v.test)));
                      }}
                    >
                      改装 {k}
                    </button>
                  ))}
                </div>
              </div>
            )
          }
          note={
            curves === "loading" ? (
              "正在计算曲线（裁判侧重新仿真，并在沙箱里运行学习者的 predict.py）…"
            ) : !c ? (
              "这一轮还没有可画的曲线。"
            ) : activeKey && variant ? (
              <>
                改装 <span className="mono">{activeKey}</span> = <b className="mono">{fmt(variant.value, 4)}</b>
                {variant.current ? "（原尺寸）" : variant.test ? "（裁判的改装考题）" : ""}。学习者没见过改装后的装置；
                裁判考题上理论命中率 <b className="mono">{pct(modRate)}</b>。
              </>
            ) : (
              <>
                其余旋钮固定在学习者常用值（{Object.entries(c.fixed)
                  .filter(([k]) => k !== c.knob)
                  .map(([k, v]) => `${k}=${v.toFixed(2)}`)
                  .join("，")}）。橙色虚线是它提交的理论，蓝线是真值，墨点是这条线附近的实际观测。分布内命中率{" "}
                <b className="mono">{pct(hitRates.in_distribution)}</b>。
              </>
            )
          }
        >
          {c && variant && <ResponseSlice curves={c} variant={variant} label={label} ss={ss} god={god} ranges={ranges} />}
          {activeKey && modVariants.length > 1 && (
            <input
              className="mod-slider"
              type="range"
              min={0}
              max={modVariants.length - 1}
              value={Math.min(modIdx, modVariants.length - 1)}
              onChange={(e) => setModIdx(Number(e.target.value))}
              aria-label="改装尺寸"
            />
          )}
        </Panel>

        <Panel idx="04" title="它怎么选实验" className="d" note="按时间连线：先大范围摸底，再在目标区密集校准。方块是考试作答（绿 = 命中，红 = 未命中）。">
          <KnobPath ss={ss} knobs={card.knobs} selected={sel} onSelect={select} />
        </Panel>

        <Panel
          idx="06"
          title={`学习者实际拿到的数据 · 实验 #${(sel ?? 0) + 1}`}
          className="f"
          note={selExp ? `旋钮 ${Object.entries(selExp.knobs).map(([k, v]) => `${k}=${v.toFixed(3)}`).join("  ")}；预测 ${selExp.prediction ? fmt(selExp.prediction[0]) : "无落点"}，观测 ${selExp.outcome ? fmt(selExp.outcome[0]) : "无落点"}` : ""}
        >
          <div className="pair">
            <div className="traces">{selExp && <Traces exp={selExp} width={360} />}</div>
            <div className="mini3d">
              <DeviceScene
                scene={scene}
                replay={replay}
                replayKey={`${round}${label}${sel}`}
                marks={{ prediction: selExp?.prediction, observed: selExp?.outcome, truth: god ? (replay?.outcome ?? null) : null }}
                god={god}
              />
              <span className="label mini-cap">裁判视角 · 学习者看不到</span>
            </div>
          </div>
        </Panel>

        <Panel
          idx="07"
          title="实验前 vs 实验后"
          className="g"
          note={
            <>
              前测 <b className="mono">{pre ? `${pre.hits}/${pre.total}` : "—"}</b>（零实验）→ 考试 <b className="mono">{exam ? `${exam.hits}/${exam.total}` : "—"}</b>
              ；横线是 ±容差，圆点是落点。
            </>
          }
        >
          <ExamStrip ss={ss} goal={goal} tol={tol} width={Math.max(280, rightSize.width)} />
        </Panel>

        <Panel idx="08" title="工作节奏" className="h" note="实验、写或运行分析脚本、作答在会话中的分布；竖线是提交理论的时刻。">
          <div ref={rhythmRef} className="fill">
            <Rhythm ss={ss} width={rhythmSize.width} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

/** The knob this instance's exam answers vary most: the one it steers the outcome with. */
function controllerKnob(ss: SessionState | undefined, knobs: Knob[] | undefined): string | undefined {
  const exam = (ss?.answers ?? []).filter((a) => a.phase === "exam" && a.knobs).map((a) => a.knobs!);
  if (!knobs?.length || exam.length < 2) return undefined;
  const spread = knobs.map((k) => (deviation(exam, (kn) => kn[k.name]) ?? 0) / (k.high - k.low || 1));
  return knobs[spread.indexOf(Math.max(...spread))].name;
}

function ErrorSparkWide(props: Omit<Parameters<typeof ErrorSpark>[0], "width" | "height">) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  return (
    <div ref={ref} className="chart-box">
      <ErrorSpark {...props} width={width} height={height} />
    </div>
  );
}
