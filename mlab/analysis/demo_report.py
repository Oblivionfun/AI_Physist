"""Export a finished run as a public demo: timeline, figures and agent artifacts.

World values are revealed only after the run, for evaluating belief estimates.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import matplotlib.pyplot as plt

from mlab.agents.backend import parse_stream
from mlab.orchestrator import default_runs_dir

PROJECT = Path(__file__).resolve().parents[2]


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def _pct(x) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def _fig_prediction(rounds: list[dict], out: Path) -> Path | None:
    ok = [r for r in rounds if r.get("status") == "ok"]
    if not ok:
        return None
    fig, axes = plt.subplots(1, len(ok), figsize=(5 * len(ok), 3.6), squeeze=False)
    for ax, r in zip(axes[0], ok, strict=True):
        for m in r["metrics"]:
            pts = [(i, e) for i, e in m["self_pred_err"] if e is not None]
            pro = [(i, e) for i, e in m["probe_pred_err"] if e is not None]
            if pts:
                ax.plot(*zip(*pts, strict=True), ".-", alpha=0.7, label=f"{m['label']} own experiments")
            if pro:
                ax.plot(*zip(*pro, strict=True), "s", ms=7, label=f"{m['label']} referee probes")
        ax.axhline(1.0, color="k", lw=0.8, ls="--")
        ax.set_yscale("log")
        ax.set_xlabel("experiment index")
        ax.set_ylabel("|prediction - truth| / tolerance")
        ax.set_title(f"round {r['round']}: {r['device']}")
        ax.legend(fontsize=7)
    fig.tight_layout()
    path = out / "prediction_error.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def _fig_scores(rounds: list[dict], out: Path) -> Path | None:
    ok = [r for r in rounds if r.get("status") == "ok"]
    if not ok:
        return None
    labels, pre, exam, bb = [], [], [], []
    for r in ok:
        for m in r["metrics"]:
            labels.append(f"r{r['round']}{m['label']}")
            pre.append(m["pretest_rate"])
            exam.append(m["exam_rate"])
            bb.append(r["controls"].get("blackbox_exam_success"))
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=(1.2 * len(labels) + 3, 3.4))
    ax.bar([i - 0.25 for i in x], pre, 0.25, label="pretest (no experiments)")
    ax.bar(list(x), exam, 0.25, label="exam (after lab)")
    ax.bar([i + 0.25 for i in x], [b or 0 for b in bb], 0.25, label="black-box baseline exam")
    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("success rate")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = out / "success.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def build(run_id: str, runs_dir: Path | None = None, dest: Path | None = None) -> Path:
    plt.switch_backend("Agg")
    root = (runs_dir or default_runs_dir()) / run_id
    dest = dest or PROJECT / "demo" / "recorded" / run_id
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "figures").mkdir(parents=True)
    summary = _load(root / "referee" / "summary.json") or {}
    secrets = _load(root / "referee" / "secrets.json") or {}
    rounds = summary.get("rounds", [])

    shutil.copytree(root / "public", dest / "public")
    for name in ("design_log.md", "designs"):
        src = root / "builder" / name
        if src.is_dir():
            shutil.copytree(src, dest / "builder" / name)
        elif src.exists():
            (dest / "builder").mkdir(exist_ok=True)
            shutil.copy(src, dest / "builder" / name)
    for ws in sorted((root / "learner").glob("*")):
        if ws.is_dir():
            for name in ("notebook.md", "predict.py", "belief.json"):
                if (ws / name).exists():
                    (dest / "learner" / ws.name).mkdir(parents=True, exist_ok=True)
                    shutil.copy(ws / name, dest / "learner" / ws.name / name)

    audit = summary.get("isolation_audit")
    audit_text = ("not recorded" if audit is None else "clean" if audit.get("clean")
                  else f"HITS FOUND: {audit}")
    lines = [f"# Run `{run_id}`", "",
             (f"- builder: `{summary.get('builder')}`; learner: `{summary.get('learner')}`; "
             f"certification profile: `{summary.get('profile')}`"),
             f"- isolation audit (canaries): {audit_text}",
             "", "## Timeline", ""]
    builder_calls = summary.get("builder_sessions", [])
    for r in rounds:
        lines.append(f"### Round {r['round']}: {r['status']}")
        for a in r.get("attempts", []):
            cert = _load(root / "referee" / "certificates" / f"r{r['round']}_a{a['attempt']}.json")
            verdict = "CERTIFIED" if a["passed"] else f"REJECTED - {a['first_failure']}"
            lines.append(f"- builder attempt {a['attempt']}: {verdict} ({a['seconds']} s)")
            if cert and not a["passed"]:
                lines.append("  <details><summary>certificate</summary>\n\n```\n" + cert["report"]
                             + "\n```\n</details>")
        if r.get("status") == "ok":
            lines.append(f"- device `{r['device']}` (v{r['version']}); twins A and B studied separately")
            for m in r["metrics"]:
                first, last = m["pred_trend"]
                lines.append(
                    f"  - learner {m['label']}: pretest {_pct(m['pretest_rate'])}, exam {_pct(m['exam_rate'])}, "
                    f"experiments {m['experiments_used']}/{m['budget']}, prediction error first third "
                    f"{first if first is None else round(first, 2)} -> last third "
                    f"{last if last is None else round(last, 2)} tolerances; theory hit rates "
                    + ", ".join(f"{k}: {_pct(v['hit_rate'])}" for k, v in m["theory"].items()))
                if m["belief"]:
                    lines.append("    - belief: " + ", ".join(
                        f"{k} unit error {v['unit_error']:.2f}{' (covered)' if v['covered'] else ''}"
                        for k, v in m["belief"].items()))
            lines.append(f"- swap test (hit rates): {r['swap']}")
            lines.append(f"- controls: {r['controls']}")
        lines.append("")
    if builder_calls:
        lines += ["## Builder sessions", ""]
        for b in builder_calls:
            t = root / "referee" / "transcripts" / f"builder_call{b['call']:02d}.jsonl"
            _, final, tools, _usage = parse_stream(t)
            lines.append(f"- call {b['call']} (round {b['round']}): submitted={b['submitted']}, "
                         f"{tools} tool calls, {sum(x['seconds'] for x in b['runs']):.0f} s")
            if final:
                lines.append("  <details><summary>builder's final message</summary>\n\n"
                             + final.strip()[:4000] + "\n</details>")
    learner_sessions = summary.get("learner_sessions", [])
    if learner_sessions:
        lines += ["", "## Learner sessions (main lineage)", ""]
        for s in learner_sessions:
            lines.append(f"- {s['tag']}: final phase {s['final_phase']}, {s['rpc_calls']} lab calls "
                         f"({s['rpc_errors']} rejected), {sum(x['seconds'] for x in s['runs']):.0f} s")
    figs = [_fig_prediction(rounds, dest / "figures"), _fig_scores(rounds, dest / "figures")]
    lines += ["", "## Figures", ""] + [f"![{f.stem}](figures/{f.name})" for f in figs if f]
    lines += ["", "## World values (revealed after the run)", "",
              "```json", json.dumps({k: round(v, 5) for k, v in secrets.get("world", {}).items()},
                                    indent=1), "```", "",
              ("Raw material: `public/` (hash-chained channel log, task cards, round reports), "
              "`builder/` (design log and submitted designs), `learner/` (notebooks and theories).")]
    (dest / "index.md").write_text("\n".join(lines) + "\n")
    return dest


if __name__ == "__main__":
    print(build(sys.argv[1]))
