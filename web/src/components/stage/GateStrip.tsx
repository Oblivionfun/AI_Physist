import { checkName, DECISION_NAME, fmt } from "../../data/derive";
import type { AttemptState } from "../../data/fold";
import type { Verdict } from "../../data/types";

/** Certificate gates in order; the strip stops lighting at the first failure. */
export function GateStrip({ attempt, pending }: { attempt?: AttemptState; pending: boolean }) {
  if (!attempt) return null;
  const verdicts = attempt.cert?.verdicts ?? [];
  return (
    <div className="gates" aria-label="可解性证书">
      <div className="gates-head">
        <span className="label">
          <b>02</b> 裁判 · 证书 · 第 {attempt.attempt} 次提交
        </span>
        <span className="mono muted">{attempt.device}</span>
        {pending ? (
          <span className="tag">认证中…</span>
        ) : attempt.cert?.passed ? (
          <span className="tag pass">通过 · {fmt(attempt.cert.seconds, 0)} s</span>
        ) : (
          <span className="tag fail">退回</span>
        )}
      </div>
      <ol className="gates-row">
        {pending && <li className="gate pending">C0 → C3 逐项检查中</li>}
        {verdicts.map((v, i) => (
          <Gate key={i} v={v} />
        ))}
      </ol>
      {!pending && !attempt.cert?.passed && <FailDetail v={verdicts.find((v) => v.decision === "fail")} />}
    </div>
  );
}

function Gate({ v }: { v: Verdict }) {
  const ratio = v.value != null && v.threshold ? Math.min(2, v.value / v.threshold) : null;
  return (
    <li className={`gate ${v.decision}`} title={v.detail}>
      <span className="gate-code mono">{v.code}</span>
      <span className="gate-name">{checkName(v.title)}</span>
      {ratio != null && (
        <span className="gate-meter" aria-hidden>
          <i style={{ width: `${(ratio / 2) * 100}%` }} />
          <b style={{ left: "50%" }} />
        </span>
      )}
      <span className="gate-val mono">
        {v.value != null ? fmt(v.value, 3) : DECISION_NAME[v.decision] ?? v.decision}
        {v.threshold != null && <span className="muted"> / {v.threshold}</span>}
      </span>
    </li>
  );
}

function FailDetail({ v }: { v?: Verdict }) {
  if (!v) return null;
  return (
    <p className="gate-detail">
      <span className="tag fail">
        {v.code} {checkName(v.title)}
      </span>{" "}
      {v.detail}
    </p>
  );
}
