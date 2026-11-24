"""Reproducible relay demonstration with THREE deterministic fixture processes.

These workers are not LLM agents. They exercise the installed orchestrator's
real CLI, durable handoff and checks. No external provider or daemon is started.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from suite_safety import new_external_path, read_json, write_new_json
from suite_identity import current_identity


def _public(value):
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items() if k not in {"lease_token", "token_hash"}}
    if isinstance(value, list): return [_public(x) for x in value]
    return value


def _cli(skill, args, records, token=None, expected="PASS"):
    argv = [sys.executable, "-B", str(skill / "scripts/suite_orchestrator.py"), "task", *map(str, args)]
    env = dict(os.environ); env.pop("BAGO_RELAY_TOKEN", None); env["PYTHONDONTWRITEBYTECODE"] = "1"
    if token: env["BAGO_RELAY_TOKEN"] = token
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=100, env=env)
    payload = json.loads(proc.stdout)
    records.append({"argv": argv, "returncode": proc.returncode, "result": _public(payload), "stderr": proc.stderr})
    ok = proc.returncode == 0 and payload["status"] == "PASS"
    if (expected == "PASS" and not ok) or (expected == "FAIL" and (proc.returncode == 0 or payload["status"] != "FAIL")):
        raise RuntimeError(f"unexpected CLI result: {_public(payload)}")
    return payload


def _worker(phase, skill, output):
    state = output / "state"; records = []
    base = ["--state-dir", state]
    if phase == "A":
        claim = _cli(skill, ["collaborate", "claim", *base, "--check", "work", "--worker", "agent-A"], records)
        (output / "workspace/notes.txt").write_text("Input checked: 21; expected result: 42.\n", encoding="utf-8")
        offer = _cli(skill, ["collaborate", "offer", *base, "--check", "work", "--worker", "agent-A",
            "--to-worker", "agent-B", "--context", output / "context.json", "--reason", "explicit-context-budget-fixture"], records, claim["lease_token"])
        _cli(skill, ["collaborate", "heartbeat", *base, "--check", "work", "--worker", "agent-A"],
             records, claim["lease_token"], expected="FAIL")
        write_new_json(output / "offer.json", offer)
    else:
        check = "work" if phase == "B" else "verify"
        worker = "agent-B" if phase == "B" else "agent-C-verifier"
        if phase == "B":
            offer = read_json(output / "offer.json")
            claim = _cli(skill, ["collaborate", "accept", *base, "--worker", worker,
                "--handoff", offer["handoff_id"], "--ack-sha256", offer["sha256"]], records)
        else:
            claim = _cli(skill, ["collaborate", "claim", *base, "--check", check, "--worker", worker], records)
        token = claim["lease_token"]
        _cli(skill, ["run-check", *base, "--check", check, "--worker", worker, "--timeout", "30", "--",
                     sys.executable, "-B", f"{check}_check.py"], records, token)
        _cli(skill, ["consume", *base, "--check", check, "--worker", worker], records, token)
        _cli(skill, ["collaborate", "finish", *base, "--check", check, "--worker", worker], records, token)
    result = {"status": "PASS", "worker_phase": phase, "pid": os.getpid(),
              "worker_type": "DETERMINISTIC_FIXTURE_NOT_LLM", "steps": records}
    write_new_json(output / f"worker-{phase}.json", result)
    return result


def run_demo(skill: Path, output: Path):
    skill = Path(skill).resolve(strict=True)
    identity = current_identity(skill)
    output = new_external_path(output, (skill,))
    # A new parent of the payload would also be an inappropriate output root.
    if skill.is_relative_to(output): raise ValueError("demo output overlaps installed payload")
    output.mkdir(parents=True)
    workspace = output / "workspace"; workspace.mkdir()
    (workspace / "input.txt").write_text("21\n", encoding="utf-8")
    (workspace / "work_check.py").write_text(
        "from pathlib import Path\nimport json\n"
        "n=int(Path('input.txt').read_text())\n"
        "Path('output.json').write_text(json.dumps({'answer': n*2}))\n"
        "print('work: answer materialized')\n", encoding="utf-8")
    (workspace / "verify_check.py").write_text(
        "from pathlib import Path\nimport json\n"
        "assert json.loads(Path('output.json').read_text()) == {'answer': 42}\n"
        "assert Path('input.txt').read_text().strip() == '21'\n"
        "print('independent fixture verifier: expected output observed')\n", encoding="utf-8")
    plan = {"schema": "bago.suite.task.plan.v1", "mission_id": "relay-demo", "candidate_id": "fixture-v1",
            "operation": "REPAIR", "scope": ["input.txt", "work_check.py", "verify_check.py"], "max_rounds": 4,
            "checks": [{"id": "work", "kind": "execution", "mandatory": True, "depends_on": [],
                        "artifacts": [{"path": "output.json", "schema": None}]},
                       {"id": "verify", "kind": "execution", "mandatory": True, "depends_on": ["work"], "artifacts": []}]}
    config = {"schema": "bago.suite.collaboration.v1", "workers": [
        {"id": "agent-A", "role": "executor"}, {"id": "agent-B", "role": "executor"},
        {"id": "agent-C-verifier", "role": "verifier"}], "verification_checks": ["verify"],
        "lease_seconds": 300, "max_claims": 8, "max_handoffs": 4, "max_checkpoints": 8}
    context = {"schema": "bago.suite.relay.context.v1", "summary": "Continue one fixed-candidate fixture, not a live coding task.",
               "completed": ["Read input 21 and recorded expected output 42"], "pending": ["Execute work check; submit its evidence"],
               "decisions": ["Independent verifier owns the verify check"], "risks": ["Logical worker roles do not authenticate a host agent"],
               "artifacts": [{"root": "workspace", "path": "notes.txt"}]}
    for name, value in [("plan.json", plan), ("config.json", config), ("context.json", context)]:
        write_new_json(output / name, value)
    records = []; base = ["--state-dir", output / "state"]
    result = {"schema": "bago.suite.relay.demo.v1", "status": "FAIL", "identity": identity,
              "capability_id": "BAGO-AGENT-RELAY-001", "workers": [], "controls": {},
              "boundary": "installed CLI, real SQLite and deterministic child processes; not LLM/host-agent integration",
              "host_agents": "NOT_RUN", "windows": "NOT_RUN"}
    try:
        _cli(skill, ["init", *base, "--workspace", workspace, "--plan", output / "plan.json"], records)
        _cli(skill, ["collaborate", "enable", *base, "--config", output / "config.json"], records)
        _cli(skill, ["round", *base], records)
        for phase in ("A", "B", "C"):
            if phase == "B":
                offer = read_json(output / "offer.json"); notes = workspace / "notes.txt"; original = notes.read_bytes()
                notes.write_text("INJECTED NEGATIVE FIXTURE: altered evidence\n", encoding="utf-8")
                rejected = _cli(skill, ["collaborate", "accept", *base, "--worker", "agent-B",
                    "--handoff", offer["handoff_id"], "--ack-sha256", offer["sha256"]], records, expected="FAIL")
                if "artifact changed" not in rejected.get("error", ""):
                    raise RuntimeError("negative control failed for an unrelated reason")
                result["controls"]["altered_artifact_rejected"] = "PASS"
                # Explicit reset of a disposable negative-test input, not a re-signed receipt.
                notes.write_bytes(original)
            proc = subprocess.run([sys.executable, "-B", str(skill / "scripts/suite_relay_demo.py"),
                "--phase", phase, "--skill", str(skill), "--output", str(output)],
                capture_output=True, text=True, timeout=150,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            (output / f"worker-{phase}.stdout.log").write_text(proc.stdout, encoding="utf-8")
            (output / f"worker-{phase}.stderr.log").write_text(proc.stderr, encoding="utf-8")
            if proc.returncode: raise RuntimeError(f"fixture worker {phase} exited {proc.returncode}: {proc.stderr[-2000:]}")
            worker = read_json(output / f"worker-{phase}.json")
            result["workers"].append({"phase": phase, "pid": worker["pid"], "type": worker["worker_type"], "status": worker["status"]})
            _cli(skill, ["collaborate", "guide", *base], records)
        result["closure"] = _cli(skill, ["close", *base], records)
        if result["closure"]["task_status"] != "CLOSED": raise RuntimeError("fixture mission did not close")
        result["controls"]["stale_lease_rejected"] = "PASS"
        result["controls"]["separate_worker_processes"] = "PASS" if len({w["pid"] for w in result["workers"]}) == 3 else "FAIL"
        if result["controls"]["separate_worker_processes"] != "PASS": raise RuntimeError("PID reuse; inspect process receipts")
        result["final_task"] = _cli(skill, ["status", *base], records)
        if current_identity(skill) != identity: raise RuntimeError("installed payload changed during demonstration")
        result["status"] = "PASS"
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["steps"] = records
    write_new_json(output / "DEMONSTRATION.json", result)
    return {"status": result["status"], "capability_id": result["capability_id"], "workers": result["workers"],
            "controls": result["controls"], "evidence": str(output / "DEMONSTRATION.json"),
            "boundary": result["boundary"], "host_agents": "NOT_RUN", "windows": "NOT_RUN",
            **({"error": result["error"]} if "error" in result else {})}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=["A", "B", "C"], required=True)
    p.add_argument("--skill", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    _worker(args.phase, args.skill, args.output)
    print(json.dumps({"status": "PASS", "phase": args.phase, "type": "DETERMINISTIC_FIXTURE_NOT_LLM"}))
