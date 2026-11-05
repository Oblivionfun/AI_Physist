"""lab: the learner's only interface to the device. Standard library only.

This file is copied into the learner workspace; it must never import mlab.
Usage: ./lab <command> [args]   (run ./lab help)
"""

import argparse
import json
import socket
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG = HERE / ".lab.json"


def call(method, **args):
    cfg = json.loads(CONFIG.read_text())
    req = json.dumps({"token": cfg["token"], "method": method, "args": args}) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(cfg["socket"])
        s.sendall(req.encode())
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    reply = json.loads(buf.decode())
    if not reply.get("ok"):
        print("ERROR: " + reply.get("error", "unknown error"))
        sys.exit(1)
    return reply["result"]


def session_dir():
    cfg = json.loads(CONFIG.read_text())
    d = HERE / "data" / cfg.get("session", "session")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _json_arg(text, what):
    p = Path(text)
    raw = p.read_text() if p.suffix == ".json" and p.exists() else text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"ERROR: {what} must be JSON (or a path to a .json file), got: {text}")
        sys.exit(2)


def _summarize_obs(obs, rows=10):
    lines = [
        (f"experiment #{obs['index']}{' (referee probe)' if obs['probe'] else ''}: "
        f"knobs={obs['knobs']} prediction={obs['prediction']}"),
        f"  outcome={obs['outcome']} status={obs['status']}",
    ]
    times = obs["times"]
    if times:
        step = max(1, len(times) // rows)
        idx = list(range(0, len(times), step))
        if idx[-1] != len(times) - 1:
            idx.append(len(times) - 1)
        header = "  t      " + "  ".join(f"{k:>20s}" for k in obs["traces"])
        lines.append(header)
        for i in idx:
            cells = []
            for v in obs["traces"].values():
                x = v[i]
                cells.append(f"{x:>20.4f}" if not isinstance(x, list)
                             else f"{'(' + ','.join(f'{c:.3f}' for c in x) + ')':>20s}")
            lines.append(f"  {times[i]:<6.2f} " + "  ".join(cells))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lab", description="Interface to the device under study.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("card", help="print the task card (also saved to card.json)")
    sub.add_parser("status", help="current phase, experiments used, whether a probe is due")
    sub.add_parser("goal", help="current pretest/exam goal")
    a = sub.add_parser("answer", help="answer the current pretest/exam goal")
    a.add_argument("knobs", help='JSON object, e.g. \'{"name": 0.5}\'')
    e = sub.add_parser("exp", help="run one experiment (prediction required first)")
    e.add_argument("knobs", help="JSON object of knob values")
    e.add_argument("prediction", help="JSON list: your predicted outcome")
    sub.add_parser("probe", help="get the knob values of a due referee probe")
    pr = sub.add_parser("probe-result", help="predict the due probe, then see its result")
    pr.add_argument("prediction", help="JSON list: your predicted outcome")
    sub.add_parser("finish-lab", help="end the lab phase")
    t = sub.add_parser("submit-theory", help="submit predict.py (+ optional belief JSON)")
    t.add_argument("path", help="path to predict.py")
    t.add_argument("--belief", help="JSON file: {\"estimates\": {name: {value, low, high}}}")
    r = sub.add_parser("report", help="finish with optional tickets; reveals pretest/exam results")
    r.add_argument("tickets", nargs="?", help='JSON list: [{"category": ..., "text": ...}]')
    args = ap.parse_args(argv)

    if args.cmd == "card":
        card = call("card")
        (HERE / "card.json").write_text(json.dumps(card, indent=2))
        print(f"{card['title']} (version {card['version']})\n\n{card['goal_text']}\n")
        print(card["manual"] + "\n")
        print("Knobs:")
        for k in card["knobs"]:
            print(f"  {k['name']}: [{k['low']}, {k['high']}] {k['unit']}  {k['description']}")
        o = card["outcome"]
        print(f"Outcome: {o['description']}; goal space {o['goal_space']}; tolerance "
              f"{o['tolerance']}; outcome noise sd {o['noise']}")
        print("Sensors:")
        for s in card["sensors"]:
            print(f"  {s['name']}: {s['kind']} of '{s['part']}', noise sd {s['noise']}, {s['rate_hz']} Hz")
        if card["unknowns"]:
            print("Unknown quantities (datasheet ranges):")
            for u in card["unknowns"]:
                print(f"  {u['name']}: {u['description']}, between {u['low']} and {u['high']} {u['unit']}")
        if card["modifiable"]:
            print("Modifiable visible dimensions (keys of `visible` in predict):")
            for m in card["modifiable"]:
                print(f"  {m['name']}: now {m['current']}, may be set within [{m['low']}, {m['high']}]")
        if card["changelog"]:
            print("Changes since the previous version: " + "; ".join(card["changelog"]))
        print("\n" + card["rules"])
    elif args.cmd == "status":
        print(json.dumps(call("status")))
    elif args.cmd == "goal":
        print(json.dumps(call("current_goal")))
    elif args.cmd == "answer":
        print(json.dumps(call("answer", knobs=_json_arg(args.knobs, "knobs"))))
    elif args.cmd == "exp":
        obs = call("experiment", knobs=_json_arg(args.knobs, "knobs"),
                   prediction=_json_arg(args.prediction, "prediction"))
        path = session_dir() / f"exp_{obs['index']:03d}.json"
        path.write_text(json.dumps(obs))
        print(_summarize_obs(obs) + f"\n  full data: {path.relative_to(HERE)}")
    elif args.cmd == "probe":
        print(json.dumps(call("probe")))
    elif args.cmd == "probe-result":
        obs = call("probe_result", prediction=_json_arg(args.prediction, "prediction"))
        path = session_dir() / f"exp_{obs['index']:03d}.json"
        path.write_text(json.dumps(obs))
        print(_summarize_obs(obs) + f"\n  full data: {path.relative_to(HERE)}")
    elif args.cmd == "finish-lab":
        print(json.dumps(call("finish_lab")))
    elif args.cmd == "submit-theory":
        code = Path(args.path).read_text()
        belief = json.loads(Path(args.belief).read_text()) if args.belief else None
        print(json.dumps(call("submit_theory", code=code, belief=belief)))
    elif args.cmd == "report":
        tickets = _json_arg(args.tickets, "tickets") if args.tickets else []
        out = call("field_report", tickets=tickets)
        (session_dir() / "results.json").write_text(json.dumps(out["results"], indent=2))
        print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
