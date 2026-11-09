import type { ReactNode } from "react";
import { checkName, examScore, expRows, fmt, median, pct, roundsOf, tolerance } from "../../data/derive";
import type { RunState } from "../../data/fold";
import type { Label } from "../../data/types";
import { useFullState } from "../../state/runState";
import { useStore, type Focus, type View } from "../../state/store";

interface Item {
  text: ReactNode;
  go?: { view: View; at?: number; focus?: Focus };
  tone?: "pass" | "fail" | "note";
}

function jump(g: NonNullable<Item["go"]>) {
  const st = useStore.getState();
  st.setView(g.view);
  if (g.focus) st.setFocus(g.focus);
  if (g.at != null) st.seekReal(g.at);
}

function isolation(s: RunState): Item[] {
  const out: Item[] = [
    {
      text: "三层隔离：能力层（学习者只能经 RPC 白名单和令牌访问装置）、系统层（每个角色一份 Seatbelt 策略）、信息层（任务卡由构造记录自动生成，并经过泄漏扫描）。",
      tone: "note",
    },
  ];
  const end = s.end;
  if (end) {
    out.push({
      text: (
        <>
          canary 交叉审计：{end.isolation_audit.clean ? "两侧都没有出现对方或裁判的 canary" : `发现 ${end.isolation_audit.learner_side_hits.length + end.isolation_audit.builder_side_hits.length} 处泄漏`}。
        </>
      ),
      tone: end.isolation_audit.clean ? "pass" : "fail",
    });
    out.push({
      text: `哈希链信道日志 ${end.chain_entries} 条，校验${end.chain_ok ? "完整" : "失败"}：每条跨边界消息都可审计，篡改会被发现。`,
      tone: end.chain_ok ? "pass" : "fail",
    });
  }
  if (s.audit) {
    out.push({
      text: `观察窗自身的访问令牌（${s.audit.viewer_tokens} 个）没有出现在任何 Agent 的工作区或会话记录里。`,
      tone: s.audit.clean ? "pass" : "fail",
    });
  }
  const kinds = new Map<string, number>();
  for (const c of s.channel) kinds.set(c.route, (kinds.get(c.route) ?? 0) + 1);
  out.push({
    text: `信道上的消息：${[...kinds.entries()].map(([k, v]) => `${k} ${v} 条`).join("；")}。学习者的推理、笔记和代码从不发给建造者。`,
    go: { view: "stage", at: s.channel[0]?.ts },
  });
  return out;
}

function solvability(s: RunState): Item[] {
  const out: Item[] = [];
  for (const rs of roundsOf(s)) {
    for (const a of rs.attempts) {
      if (!a.cert) continue;
      const fail = a.cert.verdicts.find((v) => v.decision === "fail");
      out.push({
        text: fail ? (
          <>
            R{rs.round} 第 {a.attempt} 次提交被退回：{fail.code} {checkName(fail.title)} {fmt(fail.value, 3)}（阈值 {fail.threshold}）
          </>
        ) : (
          <>
            R{rs.round} 第 {a.attempt} 次提交通过：
            {a.cert.verdicts
              .filter((v) => v.value != null && ["existence", "necessity (nominal parameters)", "identifiability (posterior predictive)"].includes(v.title))
              .map((v) => `${checkName(v.title)} ${fmt(v.value, 3)}`)
              .join("，")}
          </>
        ),
        tone: fail ? "fail" : "pass",
        go: { view: "stage", at: a.cert.ts + 1 },
      });
    }
  }
  const bb = roundsOf(s)
    .map((r) => r.report?.controls.blackbox_exam_success)
    .filter((x): x is number => x != null);
  if (bb.length)
    out.push({
      text: `每轮都跑一个不建模的黑盒基线：命中率 ${bb.map((x) => pct(x)).join("、")}。它满分时，成绩单会提示建造者“可以被暴力拟合”。`,
      go: { view: "accumulation" },
      tone: "note",
    });
  return out;
}

function learning(s: RunState): Item[] {
  const out: Item[] = [];
  for (const rs of roundsOf(s)) {
    for (const label of ["A", "B"] as Label[]) {
      const ss = rs.sessions[label];
      if (!ss) continue;
      const pre = examScore(ss, "pretest");
      const exam = examScore(ss, "exam");
      const rows = expRows(ss, tolerance(rs));
      const third = Math.max(1, Math.floor(rows.length / 3));
      const a = median(rows.slice(0, third).map((r) => r.err ?? NaN));
      const b = median(rows.slice(-third).map((r) => r.err ?? NaN));
      out.push({
        text: (
          <>
            R{rs.round} 实例 {label}：前测 <b>{pre ? `${pre.hits}/${pre.total}` : "—"}</b> → 考试 <b>{exam ? `${exam.hits}/${exam.total}` : "—"}</b>；预测误差 {fmt(a, 2)}× → {fmt(b, 2)}×
          </>
        ),
        tone: exam && exam.hits / exam.total >= 0.75 ? "pass" : "note",
        go: { view: "learning", focus: { round: rs.round, label } },
      });
    }
  }
  const swaps = roundsOf(s)
    .map((r) => r.report?.swap_test)
    .filter(Boolean) as Record<string, number | string | null>[];
  if (swaps.length) {
    const diag = swaps.flatMap((x) => [x.A_on_A, x.B_on_B]).filter((v): v is number => typeof v === "number");
    const off = swaps.flatMap((x) => [x.A_on_B, x.B_on_A]).filter((v): v is number => typeof v === "number");
    out.push({
      text: `孪生互换：自己的理论用在自己的实例上平均 ${pct(diag.reduce((a, b) => a + b, 0) / diag.length)}，换到孪生实例上平均 ${pct(off.reduce((a, b) => a + b, 0) / off.length)}。`,
      tone: "pass",
      go: { view: "accumulation" },
    });
  }
  const mods = roundsOf(s).flatMap((r) =>
    (r.report?.instances ?? []).flatMap((i) => Object.entries(i.theory_hit_rates).filter(([k, v]) => k.startsWith("modified") && v != null).map(([, v]) => v as number)),
  );
  if (mods.length) {
    out.push({
      text: `局限：改装检验（裁判公开改一个尺寸、不许再实验）命中率只有 ${pct(Math.min(...mods))} 到 ${pct(Math.max(...mods))}。学习者在训练范围内很准，但没有把物理辨识准。`,
      tone: "fail",
      go: { view: "learning" },
    });
  }
  return out;
}

function Column({ idx, title, items }: { idx: string; title: string; items: Item[] }) {
  return (
    <section className="concl-col">
      <p className="label">
        <b>{idx}</b> {title}
      </p>
      <ol>
        {items.map((it, i) => (
          <li key={i} className={it.tone ?? ""}>
            <span className="mark" aria-hidden>
              {it.tone === "pass" ? "✓" : it.tone === "fail" ? "✕" : "·"}
            </span>
            <span>{it.text}</span>
            {it.go && (
              <button className="btn small-btn" onClick={() => jump(it.go!)}>
                看证据 →
              </button>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function ConclusionView() {
  const s = useFullState();
  return (
    <div className="conclusion">
      <div className="lens-bar">
        <span className="label">
          <b>结论</b>
        </span>
        <span className="muted">题目的三个问题。每一条都由这次运行的数据生成，可以点进对应的时刻或图表。</span>
      </div>
      <div className="concl-grid">
        <Column idx="01" title="如何保证隔离" items={isolation(s)} />
        <Column idx="02" title="如何避免无解或太简单的挑战" items={solvability(s)} />
        <Column idx="03" title="如何证明学习者学到了东西" items={learning(s)} />
      </div>
    </div>
  );
}
