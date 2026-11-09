import { elapsed, examScore, expRows, median, modelShort, tolerance } from "../../data/derive";
import type { LearnerStep } from "../../data/fold";
import { useCursorState, useCursorTs } from "../../state/runState";
import { ErrorSpark } from "../charts/ErrorSpark";
import { STEP_NAME } from "../Header";
import { stageFocus } from "./focus";
import { Ticker } from "./Ticker";

const STEPS: LearnerStep[] = ["pretest", "lab", "theory", "exam", "report"];

export function LearnerColumn() {
  const s = useCursorState();
  const now = useCursorTs();
  const f = stageFocus(s);
  const card = f.rs?.card;
  const ss = f.ss;
  const tol = tolerance(f.rs);
  const rows = expRows(ss, tol);
  const third = Math.max(1, Math.floor(rows.length / 3));
  const firstMed = median(rows.slice(0, third).map((r) => r.err ?? NaN));
  const lastMed = rows.length >= 6 ? median(rows.slice(-third).map((r) => r.err ?? NaN)) : null;
  const pre = examScore(ss, "pretest");
  const exam = examScore(ss, "exam");
  const answered = (phase: "pretest" | "exam") => ss?.answers.filter((a) => a.phase === phase).length ?? 0;
  const L = s.learner;

  return (
    <aside className="col learner">
      <header className="col-head">
        <p className="label">
          <b>03</b> 学习者 · 沙箱 L {f.label && <span className="tag">实例 {f.label}</span>}
        </p>
        <p className="mono muted">{modelShort(ss?.model ?? L.model ?? s.end?.learner)}</p>
        <p className={`presence ${L.active ? "on" : ""}`}>
          <i aria-hidden />
          {L.active && L.since ? `会话中 ${elapsed(now - L.since)}` : "未在会话中"}
        </p>
      </header>

      {card ? (
        <section className="col-sec sees">
          <p className="label">它只能看到的说明书</p>
          <p className="card-title">{card.title}</p>
          <ul className="kv mono">
            {card.knobs.map((k) => (
              <li key={k.name}>
                <span>{k.name}</span>
                <span className="muted">
                  [{k.low}, {k.high}] {k.unit}
                </span>
              </li>
            ))}
            <li>
              <span>传感器</span>
              <span className="muted">{card.sensors.map((x) => x.name).join(", ") || "无"}</span>
            </li>
            <li>
              <span>未知量</span>
              <span className="muted">
                世界级 {card.unknowns.filter((u) => u.scope === "world").length} · 装置级{" "}
                {card.unknowns.filter((u) => u.scope === "device").length}
              </span>
            </li>
            <li>
              <span>预算 / 容差</span>
              <span className="muted">
                {card.protocol.budget} 次 / {card.outcome.tolerance} m
              </span>
            </li>
          </ul>
        </section>
      ) : (
        <section className="col-sec">
          <p className="muted">任务卡尚未发出：建造者的设计还没通过认证。</p>
        </section>
      )}

      {ss && (
        <>
          <section className="col-sec">
            <ol className="steps">
              {STEPS.map((st) => (
                <li key={st} className={ss.step === st ? "on" : STEPS.indexOf(st) < STEPS.indexOf(ss.step) || ss.step === "done" ? "done" : ""}>
                  {STEP_NAME[st]}
                </li>
              ))}
            </ol>
            <div className="counts mono">
              <span>前测 {pre ? `${pre.hits}/${pre.total}` : `${answered("pretest")}/${card?.protocol.pretest_goals ?? 3} 已答`}</span>
              <span>
                实验 {ss.experiments.length}/{card?.protocol.budget ?? "—"}
              </span>
              <span>考试 {exam ? `${exam.hits}/${exam.total}` : `${answered("exam")}/${card?.protocol.exam_goals ?? 8} 已答`}</span>
            </div>
          </section>

          <section className="col-sec">
            <p className="label">先预测，再观测：误差（容差倍数）</p>
            <ErrorSpark rows={rows} budget={card?.protocol.budget ?? 60} width={300} height={104} />
            {firstMed != null && (
              <p className="mono small">
                前 1/3 中位 <b>{firstMed.toFixed(2)}×</b>
                {lastMed != null && (
                  <>
                    {" "}
                    → 后 1/3 中位 <b className={lastMed < firstMed ? "hit" : "miss"}>{lastMed.toFixed(2)}×</b>
                  </>
                )}
              </p>
            )}
          </section>

          {(pre || exam) && (
            <section className="col-sec scores">
              {pre && <span className={`tag ${pre.hits ? "hit" : "miss"}`}>实验前 前测 {pre.hits}/{pre.total}</span>}
              <span aria-hidden>→</span>
              {exam && <span className={`tag ${exam.hits / exam.total >= 0.5 ? "hit" : "miss"}`}>实验后 考试 {exam.hits}/{exam.total}</span>}
            </section>
          )}
        </>
      )}

      <Ticker item={L.thought} now={now} />
    </aside>
  );
}
