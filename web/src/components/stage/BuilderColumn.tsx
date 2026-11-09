import { checkName, elapsed, fmt, modelShort } from "../../data/derive";
import type { CheckState } from "../../data/fold";
import { useCursorState, useCursorTs } from "../../state/runState";
import { stageFocus } from "./focus";
import { Ticker } from "./Ticker";

function firstFail(c: CheckState) {
  return c.verdicts.find((v) => v.decision === "fail");
}

export function BuilderColumn() {
  const s = useCursorState();
  const now = useCursorTs();
  const f = stageFocus(s);
  const rs = f.rs;
  const b = s.builder;
  const checks = (rs?.checks ?? []).slice(-6).reverse();
  const say = rs?.says.at(-1);

  return (
    <aside className="col builder">
      <header className="col-head">
        <p className="label">
          <b>01</b> 建造者 · 沙箱 B
        </p>
        <p className="mono muted">{modelShort(b.model ?? s.end?.builder)}</p>
        <p className={`presence ${b.active ? "on" : ""}`}>
          <i aria-hidden />
          {b.active && b.since ? `设计中 ${elapsed(now - b.since)}` : "等待成绩单"}
        </p>
      </header>

      <section className="col-sec">
        <p className="label">本轮提交 {f.round != null && <span className="mono">· 第 {f.round} 轮</span>}</p>
        {rs?.attempts.length ? (
          <ol className="attempts">
            {rs.attempts.map((a) => {
              const fail = a.cert?.verdicts.find((v) => v.decision === "fail");
              return (
                <li key={a.attempt}>
                  <span className="mono">#{a.attempt}</span>
                  <span className="mono">{a.device}</span>
                  {!a.cert ? (
                    <span className="tag">认证中</span>
                  ) : a.cert.passed ? (
                    <span className="tag pass">通过</span>
                  ) : (
                    <span className="tag fail" title={fail?.detail}>
                      退回 · {fail ? `${fail.code} ${checkName(fail.title)} ${fmt(fail.value, 2)}` : ""}
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        ) : (
          <p className="muted">尚未提交</p>
        )}
      </section>

      <section className="col-sec">
        <p className="label">
          本地自检 <span className="mono">· {rs?.checks.length ?? 0} 次</span>
        </p>
        <ol className="checks">
          {checks.map((c, i) => {
            const fail = firstFail(c);
            return (
              <li key={i}>
                <span className="mono muted">−{elapsed(now - c.ts)}</span>
                {c.result === "certified" ? (
                  <span className="tag pass">本地通过</span>
                ) : c.result === "rejected" ? (
                  <span className="tag fail">{fail ? `${fail.code} ${checkName(fail.title)}` : "未通过"}</span>
                ) : c.result === "construction_rejected" ? (
                  <span className="tag fail">构造被拒</span>
                ) : (
                  <span className="tag">脚本报错</span>
                )}
                {fail?.value != null && (
                  <span className="mono muted">
                    {fmt(fail.value, 2)} / {fail.threshold}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      </section>

      {say && (
        <section className="col-sec says">
          <p className="label">它的说明</p>
          <p className="clamp-5">{say.value.replace(/\*\*/g, "")}</p>
        </section>
      )}

      <Ticker item={b.thought} now={now} />
    </aside>
  );
}
