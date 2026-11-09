import { useMemo } from "react";
import { pct, roundsOf } from "../../data/derive";
import { roundMetrics } from "../../data/metrics";
import { useRelatedRuns } from "../../state/related";
import { useFullState } from "../../state/runState";
import { useStore } from "../../state/store";
import { ArmsRace } from "../charts/ArmsRace";
import { Ledger } from "../charts/Ledger";
import { RunCompare } from "../charts/RunCompare";
import { SwapMatrix } from "../charts/SwapMatrix";
import { Panel } from "./Panel";

export function AccumulationView() {
  const s = useFullState();
  const god = useStore((x) => x.god);
  const listing = useStore((x) => x.listing);
  const metrics = useMemo(() => roundMetrics(s), [s]);
  const related = useRelatedRuns(listing);
  const rounds = roundsOf(s).filter((r) => r.card);

  if (!rounds.length) {
    return (
      <div className="view-pad">
        <p className="label">还没有完成的轮次</p>
      </div>
    );
  }

  return (
    <div className="accum">
      <div className="lens-bar">
        <span className="label">
          <b>跨轮积累</b>
        </span>
        <span className="muted">学习者的知识怎样一轮轮沿用；建造者怎样根据成绩单升级挑战。</span>
      </div>
      <div className="accum-grid">
        <Panel
          idx="01"
          title="双方博弈：建造者升级 vs 学习者成绩"
          className="race"
          note="实心圆 = 考试命中率（左 A，右 B），小圆 = 前测，方块 = 不建模的黑盒基线，三角 = 裁判的参考学习者。建造者的目标是把学习者压进灰色区间，同时让黑盒做不到。"
        >
          <ArmsRace rounds={metrics} />
          <ol className="versions">
            {rounds.map((r) => {
              const m = metrics.find((x) => x.round === r.round);
              return (
                <li key={r.round}>
                  <p>
                    <span className="round-name-html">R{r.round}</span> <b>{r.card!.title}</b> <span className="mono muted">v{r.version}</span>
                  </p>
                  <ul className="changes">
                    {r.card!.changelog.slice(0, 4).map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                  <p className="small mono">
                    黑盒 {pct(m?.blackbox)} · 学习者 {pct(m?.exam.A)} / {pct(m?.exam.B)} · 提交 {r.attempts.length} 次
                  </p>
                  {r.report?.guidance && <p className="small muted clamp-3">成绩单：{r.report.guidance}</p>}
                </li>
              );
            })}
          </ol>
        </Panel>

        <Panel
          idx="02"
          title="知识账本：信念区间跨轮演化（实例 A 主线）"
          className="ledger-panel"
          note={
            <>
              每格是一轮结束时学习者对这个量的 90% 区间（灰 = 说明书给的先验范围）。
              {god ? "蓝线是真值。" : "打开上帝视角可看真值。"} 最后一行是它写给下一轮自己的话，以及下一轮前测的结果。
            </>
          }
        >
          <Ledger s={s} god={god} />
        </Panel>

        <Panel
          idx="03"
          title="孪生互换：知识绑定在交互过的实例上"
          className="swap-panel"
          note="两个实例结构相同、隐藏质量不同。对角线（自己的理论用在自己的实例上）应当高，交叉应当低：说明知识来自与这个实例的交互，而不是先验。"
        >
          <div className="swaps">
            {rounds.map((r) => (
              <SwapMatrix key={r.round} round={r.round} swap={r.report?.swap_test} />
            ))}
          </div>
        </Panel>

        <Panel
          idx="04"
          title="对照运行：同样的装置，换一个学习者"
          className="compare-panel"
          note={
            related.length
              ? "同一个世界、同样的认证装置和孪生实例，只换学习者（mlab rerun-learner）。"
              : "这个运行没有对照组。demo-1 有较弱模型和清空笔记两组对照，可在上方切换到 demo-1 查看。"
          }
        >
          {related.length > 0 && <RunCompare runs={related} />}
        </Panel>
      </div>
    </div>
  );
}
