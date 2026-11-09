import { roundsOf } from "../../data/derive";
import type { RunState } from "../../data/fold";
import { nextTimeNotes } from "../../data/metrics";
import type { Unknown } from "../../data/types";

const W = 112;

/**
 * The learner's knowledge across rounds (main lineage, instance A): one interval per unknown
 * per round. World-scoped quantities carry over and should narrow; device-scoped ones are
 * redrawn for every instance and have to be identified again.
 */
export function Ledger({ s, god }: { s: RunState; god: boolean }) {
  const rounds = roundsOf(s).filter((r) => r.card && r.sessions.A);
  const names: Unknown[] = [];
  for (const r of rounds) for (const u of r.card!.unknowns) if (!names.some((x) => x.name === u.name)) names.push(u);
  names.sort((a, b) => (a.scope === b.scope ? 0 : a.scope === "world" ? -1 : 1));

  return (
    <div className="ledger-wrap">
      <table className="ledger">
        <thead>
          <tr>
            <th className="label">未知量</th>
            {rounds.map((r) => (
              <th key={r.round}>
                <span className="round-name-html">R{r.round}</span> <span className="mono muted">{r.card!.title}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {names.map((u, i) => (
            <tr key={u.name} className={i > 0 && names[i - 1].scope !== u.scope ? "split" : ""}>
              <th className="mono">
                {u.name}
                <span className={`tag ${u.scope === "device" ? "" : "pass"}`}>{u.scope === "device" ? "每个实例重抽" : "跨轮沿用"}</span>
              </th>
              {rounds.map((r) => {
                const cu = r.card!.unknowns.find((x) => x.name === u.name);
                if (!cu) return <td key={r.round} className="muted">—</td>;
                const ss = r.sessions.A!;
                const est = (ss.final?.belief ?? ss.theory?.value.belief)?.estimates[u.name];
                const truth = r.instances?.A[u.name] ?? s.world?.[u.name];
                const f = (v: number) => ((Math.min(cu.high, Math.max(cu.low, v)) - cu.low) / (cu.high - cu.low || 1)) * W;
                return (
                  <td key={r.round}>
                    <svg width={W} height={12} className="chart">
                      <line x1={0} x2={W} y1={6} y2={6} className="prior-bar thin" />
                      {est && <line x1={f(est.low)} x2={f(est.high)} y1={6} y2={6} className="belief-bar thin" />}
                      {est && <circle cx={f(est.value)} cy={6} r={2.4} className="belief-dot" />}
                      {god && truth != null && <line x1={f(truth)} x2={f(truth)} y1={1} y2={11} className="truth-tick" />}
                    </svg>
                    {!est && <span className="muted small"> 未估计</span>}
                  </td>
                );
              })}
            </tr>
          ))}
          <tr className="notes-row">
            <th>笔记：下次要改</th>
            {rounds.map((r, i) => {
              const note = r.sessions.A!.notes.at(-1)?.value ?? "";
              const next = rounds[i + 1]?.sessions.A;
              const pre = next?.results?.value.pretest;
              const hits = pre ? pre.filter((x) => x.success).length : null;
              return (
                <td key={r.round}>
                  <p className="clamp-5 signal note">{nextTimeNotes(note)[0] ?? "（这一轮没有写）"}</p>
                  {next && (
                    <p className="small mono">
                      → 下一轮前测 <span className={`tag ${hits ? "hit" : "miss"}`}>{hits == null ? "—" : `${hits}/${pre!.length}`}</span>
                    </p>
                  )}
                </td>
              );
            })}
          </tr>
        </tbody>
      </table>
    </div>
  );
}
