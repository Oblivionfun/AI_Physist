import json

from fixtures.devices import pendulum_striker
from mlab.referee.channel import ChannelLog, verify
from mlab.referee.leak import scan


def test_channel_log_hash_chain_detects_tampering(tmp_path):
    path = tmp_path / "channel.jsonl"
    log = ChannelLog(path)
    log.append(1, "submission", {"device": "x"})
    log.append(2, "task_card", {"version": 1})
    log.append(4, "round_report", {"exam": 0.5})
    assert verify(path) == (True, 3)
    lines = path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["payload"]["version"] = 2
    lines[1] = json.dumps(entry)
    path.write_text("\n".join(lines) + "\n")
    ok, n = verify(path)
    assert not ok and n == 1


def test_channel_log_resumes_chain(tmp_path):
    path = tmp_path / "channel.jsonl"
    ChannelLog(path).append(1, "a", {})
    ChannelLog(path).append(2, "b", {})
    assert verify(path) == (True, 2)


def test_leak_scan_flags_secret_numbers_and_phrases():
    sub = pendulum_striker.submission(goal_text="The head weighs 1.734 kg, so pull it back gently.")
    issues = scan(sub, [1.73])
    assert any(i.code == "leak" for i in issues)
    sub2 = pendulum_striker.submission(goal_text="Use the oracle trick: pull back by the hidden value.")
    assert scan(sub2, [])


def test_leak_scan_ignores_public_numbers():
    sub = pendulum_striker.submission(goal_text="Targets lie between 0.05 and 0.3 m from the post.")
    assert scan(sub, [0.05 * 1.01, 0.3]) == []
