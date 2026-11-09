import { checkName, examScore, expRows, fmt, median, pct, roundsOf, tolerance } from "../../data/derive";
import type { RunState } from "../../data/fold";
import type { Label } from "../../data/types";
import type { Focus, View } from "../../state/store";

export interface Beat {
  title: string;
  body: string;
  view: View;
  at?: number;
  focus?: Focus;
  /** Start playback from `at` at this speed. */
  play?: number;
}

const firstSentence = (t: string, n = 150) => {
  const s = t.replace(/\*\*/g, "").replace(/\s+/g, " ").trim();
  const cut = s.search(/[.。!?](\s|$)/);
  const out = cut > 20 ? s.slice(0, cut + 1) : s;
  return out.length > n ? out.slice(0, n - 1) + "…" : out;
};

/** Walkthrough of a run, written from its own events, so a live run gets one too. */
export function buildBeats(s: RunState): Beat[] {
  const beats: Beat[] = [];
  const rounds = roundsOf(s);
  const r1 = rounds[0];
  if (!r1) return beats;

  beats.push({
    title: "三个进程，两道墙",
    body:
      "左边是建造者、右边是学习者，各自运行在操作系统沙箱里，互相看不到对方的文件和对话。中间是可信裁判：它持有隐藏物性的真值，所有跨边界的消息都经过它，并写进哈希链。",
    view: "stage",
    at: s.startTs,
  });

  const sub1 = r1.attempts[0];
  if (sub1) {
    beats.push({
      title: `建造者提交第一台装置：${sub1.device}`,
      body: `建造者只能用零件目录和“构造即校验”的接口搭机器。它也不知道物性真值，只知道先验范围。这一台有 ${sub1.scene.parts.length} 个零件、${sub1.scene.knobs.length} 个旋钮。`,
      view: "stage",
      at: sub1.ts + 0.5,
    });
  }

  const rejected = rounds.flatMap((r) => r.attempts.filter((a) => a.cert && !a.cert.passed).map((a) => ({ r, a })))[0];
  if (rejected) {
    const v = rejected.a.cert!.verdicts.find((x) => x.decision === "fail");
    beats.push({
      title: `证书退回：${v ? `${v.code} ${checkName(v.title)}` : "未通过"}`,
      body: v
        ? `裁判用私有种子重新认证每一次提交。这次 ${checkName(v.title)} 实测 ${fmt(v.value, 3)}，阈值 ${v.threshold}：${firstSentence(v.detail, 120)} 无解或太简单的挑战到不了学习者手里。`
        : "裁判退回了这次提交。",
      view: "stage",
      at: rejected.a.cert!.ts + 1,
    });
    const after = rejected.r.says.filter((x) => x.ts > rejected.a.cert!.ts && x.value.length > 60);
    const say = after.find((x) => /reject|fail|C\d\b|timestep|existence|necessity/i.test(x.value)) ?? after[0];
    if (say) {
      const text = say.value.replace(/\*\*/g, "");
      const m = /(?:reject|fail|C\d\b|timestep|existence|necessity)/i.exec(text);
      const from = m ? Math.max(0, text.lastIndexOf(".", m.index) + 1) : 0;
      beats.push({
        title: "建造者读了退回原因，自己诊断",
        body: `“${firstSentence(text.slice(from), 220)}”（建造者原话）`,
        view: "stage",
        at: say.ts + 0.5,
      });
    }
  }

  const passed = r1.attempts.find((a) => a.cert?.passed);
  if (r1.cardTs && r1.card) {
    beats.push({
      title: passed && passed.attempt > 1 ? `第 ${passed.attempt} 次提交通过认证` : "通过认证，任务卡发给学习者",
      body: `学习者能看到的只有自动生成的说明书：零件描述、${r1.card.knobs.length} 个旋钮（${r1.card.knobs.map((k) => k.name).join("、")}）、传感器、${r1.card.unknowns.length} 个未知量的范围。具体数值、构造代码和建造者的话都不在里面。`,
      view: "stage",
      at: r1.cardTs + 0.5,
    });
  }

  const label: Label = "A";
  const ss = r1.sessions[label];
  if (ss) {
    const tol = tolerance(r1);
    const pre = examScore(ss, "pretest");
    const firstAns = ss.answers[0];
    if (firstAns) {
      beats.push({
        title: "实验之前，先考 3 题",
        body: `前测：学习者还没做任何实验，只凭说明书和常识作答。结果 ${pre ? `${pre.hits}/${pre.total}` : "会话结束时公布"}。这是“学之前”的基线。`,
        view: "stage",
        at: firstAns.ts + 0.5,
      });
    }
    const rows = expRows(ss, tol);
    if (rows.length > 6) {
      const third = Math.floor(rows.length / 3);
      const a = median(rows.slice(0, third).map((r) => r.err ?? NaN));
      const b = median(rows.slice(-third).map((r) => r.err ?? NaN));
      beats.push({
        title: "每次实验前必须先预测",
        body: `橙色环是它的预测（半径等于容差），墨点是实际落点，连线就是误差。前三分之一实验的中位误差 ${fmt(a, 2)} 倍容差，后三分之一 ${fmt(b, 2)} 倍：预测在一次次对准现实。`,
        view: "stage",
        at: rows[2].exp.ts - 0.2,
        play: 10,
      });
      const probe = rows.find((r) => r.exp.probe);
      if (probe) {
        beats.push({
          title: "裁判探针：不由学习者挑选的实验",
          body: `每第 10 次实验的动作由裁判指定，用来排除“只在自己熟悉的地方预测得准”。这次探针的预测误差 ${fmt(probe.err, 2)} 倍容差。`,
          view: "stage",
          at: probe.exp.ts + 0.2,
        });
      }
    }
    const rep = r1.report?.instances.find((x) => x.label === label);
    if (ss.theory) {
      const mod = rep ? Object.entries(rep.theory_hit_rates).find(([k]) => k.startsWith("modified")) : undefined;
      beats.push({
        title: "提交可执行的理论，裁判拿真值检验",
        body: `学习者交出 predict.py。在探索过的范围内命中 ${pct(rep?.theory_hit_rates.in_distribution)}${
          mod ? `；裁判公开改动一个尺寸（${mod[0].replace("modified ", "")}）后只命中 ${pct(mod[1])}` : ""
        }。它学会了怎么用，但没有把物理辨识准：改装检验把两种“学会”区分开。`,
        view: "learning",
        focus: { round: r1.round, label },
      });
    }
    const exam = examScore(ss, "exam");
    const lastExam = [...ss.answers].reverse().find((x) => x.phase === "exam");
    if (lastExam) {
      beats.push({
        title: `考试：${exam ? `${exam.hits}/${exam.total}` : "8 题"}`,
        body: `考试目标到考试时才揭晓，每题只有一次机会，不能再做实验。前测 ${pre ? `${pre.hits}/${pre.total}` : "—"} → 考试 ${exam ? `${exam.hits}/${exam.total}` : "—"}。`,
        view: "stage",
        at: lastExam.ts + 0.5,
      });
    }
  }

  const sw = r1.report?.swap_test;
  if (sw) {
    beats.push({
      title: "孪生互换：知识来自交互",
      body: `同一结构、隐藏质量不同的两个实例。A 的理论用在 A 上 ${pct(sw.A_on_A as number)}，用在 B 上 ${pct(sw.A_on_B as number)}；B 的理论用在 B 上 ${pct(sw.B_on_B as number)}，用在 A 上 ${pct(sw.B_on_A as number)}。知识绑定在它交互过的那个实例上。`,
      view: "accumulation",
    });
  }

  const r2 = rounds[1];
  if (r2?.attempts[0] && r2.card) {
    beats.push({
      title: `建造者看了成绩单，升级为 ${r2.card.title}`,
      body: `成绩单只含汇总指标：“${firstSentence(r1.report?.guidance ?? "", 110)}” 新版本的变化：${r2.card.changelog.slice(0, 3).join("；")}。`,
      view: "stage",
      at: r2.attempts[0].ts + 0.5,
    });
  }

  if (rounds.length > 1) {
    beats.push({
      title: "跨轮积累",
      body: "世界级物性（弹簧、电机、摩擦）在整个运行中不变，学习者的笔记和信念逐轮沿用；装置专属的隐藏质量每个实例重抽，必须重新辨识。最后一行是它写给下一轮自己的话。",
      view: "accumulation",
    });
  }

  beats.push({
    title: "三个问题的答案",
    body: "隔离、可解、学会：每条结论都能点进对应的证据。",
    view: "conclusion",
  });
  return beats;
}
