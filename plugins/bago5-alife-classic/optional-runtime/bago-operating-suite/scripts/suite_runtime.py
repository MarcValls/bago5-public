"""Explicit Suite entry points for the unchanged RC1 runtime laboratory.

These operations create and use marked disposable projects only. They neither
launch native host agents nor invoke providers, personal history, or background
loops. Every runtime operation starts a new Python process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

from suite_safety import new_external_path, read_json, reject_links, safe_rel, strict_json, write_new_json

SCHEMA = "bago.suite.runtime-lab.v1"
FIXTURE = {"values": [2, 4, 6], "limit": 10}
SCOPE = "local explicit fixture adapters, unchanged RC1 runtime and real server-owned ExecutionGateway"


def add_parsers(subparsers) -> None:
    for kind in ("spiral", "adaptation"):
        parser = subparsers.add_parser(kind, help=f"bounded {kind} runtime laboratory")
        actions = parser.add_subparsers(dest="runtime_action", required=True)
        for action in ("init", "demo"):
            command = actions.add_parser(action)
            command.add_argument("--output", type=Path, required=True, help="new directory outside the Suite")
            if kind == "adaptation" and action == "init":
                command.add_argument("--mode", choices=("on", "off"), default="on")
        for action in (("run", "inspect", "deactivate") if kind == "spiral" else ("cycle", "inspect")):
            command = actions.add_parser(action)
            command.add_argument("--project", type=Path, required=True, help="project created by this lab's init")


def handles(args) -> bool:
    return getattr(args, "command", None) in {"spiral", "adaptation"}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _context(context):
    if isinstance(context, (str, Path)):
        return SimpleNamespace(SKILL=Path(context), candidate_identity=None)
    if isinstance(context, dict):
        return SimpleNamespace(**context)
    return context


def _identity(context) -> dict:
    identity = getattr(context, "candidate_identity", None)
    if callable(identity):
        identity = identity()
    runtime = context.SKILL / "runtime/BAGO-4.11.10"
    return {"candidate": identity, "source_lock_sha256": _hash(runtime / "SOURCE_LOCK.json"),
            "repair_provenance_sha256": _hash(runtime / "REPAIR_PROVENANCE.json"),
            "adapter_sha256": _hash(context.SKILL / "scripts/suite_runtime.py"),
            "worker_sha256": _hash(context.SKILL / "scripts/suite_runtime_worker.py")}


def _new_project(context, output: Path, kind: str, mode: str = "on") -> Path:
    project = new_external_path(output, (context.SKILL.parent,))
    project.mkdir(parents=True)
    write_new_json(project / "RUNTIME_LAB.json", {
        "schema": SCHEMA, "kind": kind, "mode": mode, "project": str(project),
        "lab_id": uuid4().hex, "identity": _identity(context),
        "authority": "explicit lab command; effects restricted to this newly created project",
        "scope": SCOPE,
    })
    write_new_json(project / "fixture.json", FIXTURE)
    return project


def _bound(context, project: Path, kind: str) -> Path:
    reject_links(project)
    project = project.expanduser().resolve(strict=True)
    marker = read_json(project / "RUNTIME_LAB.json", max_bytes=64000)
    if (not isinstance(marker, dict) or marker.get("schema") != SCHEMA
            or marker.get("kind") != kind or marker.get("project") != str(project)
            or marker.get("identity") != _identity(context)):
        raise ValueError("lab is not bound to this project, operation and exact candidate")
    return project


def _observe(project: Path, result: dict) -> list[dict]:
    """Read task effects independently of the runtime's validation/radius claim."""
    rows = []
    fixture = read_json(project / "fixture.json", max_bytes=64000)
    expected = {"count": len(fixture["values"]), "sum": sum(fixture["values"]),
                "within_limit": sum(fixture["values"]) <= fixture["limit"],
                "input_sha256": _hash(project / "fixture.json")}
    for record in result.get("effects", []):
        item = record["effect"]
        relative = safe_rel(item["path"])
        path = project.joinpath(*relative.parts)
        reject_links(path)
        if not path.resolve().is_relative_to(project):
            raise ValueError("reported effect escaped the lab")
        observed = read_json(path, max_bytes=64000)
        actual_hash = _hash(path)
        rows.append({"path": relative.as_posix(), "sha256": actual_hash,
                     "observed": observed, "status": "PASS" if (
                         observed == expected and actual_hash == item["sha256"]
                         and item["receipt"].get("ok") is True) else "FAIL"})
    return rows


def _call(context, project: Path, kind: str, operation: str, scenario: str = "normal") -> dict:
    project = _bound(context, project, kind)
    before_identity = _identity(context)
    invocation = uuid4().hex
    evidence = project / "evidence" / invocation
    evidence.mkdir(parents=True)
    command = [sys.executable, "-B", str(context.SKILL / "scripts/suite_runtime_worker.py"),
               "--skill", str(context.SKILL), "--project", str(project), "--kind", kind,
               "--operation", operation, "--invocation", invocation, "--scenario", scenario]
    env = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR") if k in os.environ}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
                "PYTHONNOUSERSITE": "1", "BAGO_AUTO_DELEGATE": "0", "BAGO_ORCHESTRATE": "0"})
    stdout, stderr, code = "", "", None
    result, observations, status, validation_error = {}, [], "FAIL", None
    try:
        child = subprocess.run(command, cwd=project, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=60)
        stdout, stderr, code = child.stdout, child.stderr, child.returncode
        result = strict_json(stdout)
        if not isinstance(result, dict):
            raise ValueError("worker result is not an object")
        if (result.get("invocation") != invocation or result.get("operation") != operation
                or result.get("project") != str(project) or type(result.get("worker_pid")) is not int):
            raise ValueError("worker result does not match the requested operation")
        observations = _observe(project, result)
        status = "PASS" if code == 0 and result.get("status") == "PASS" and all(
            row["status"] == "PASS" for row in observations) else "FAIL"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        validation_error = "worker timed out after 60 seconds"
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError) as exc:
        validation_error = f"{type(exc).__name__}: {exc}"
    try:
        after_identity = _identity(context)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        after_identity = {"error": f"{type(exc).__name__}: {exc}"}
        validation_error = "candidate identity unavailable after runtime operation"
    if before_identity != after_identity:
        validation_error = "candidate content changed during runtime operation"
    if validation_error is not None:
        status = "FAIL"
    (evidence / "stdout.log").write_text(stdout, encoding="utf-8")
    (evidence / "stderr.log").write_text(stderr, encoding="utf-8")
    report = {"status": status, "operation": operation, "kind": kind, "scope": SCOPE,
              "command": command, "returncode": code, "worker": result,
              "independent_observations": observations, "identity": before_identity,
              "identity_after": after_identity, "validation_error": validation_error,
              "project": str(project), "evidence": str(evidence / "result.json"),
              "partial_effects_possible_on_failure": status != "PASS",
              "native_host_agents": "NOT_RUN", "live_BAGO5_ADL": "NOT_RUN"}
    write_new_json(evidence / "result.json", report)
    return report


def _negative(report: dict, operation: str, error_type: str | None = None, text: str = "") -> bool:
    worker = report.get("worker", {})
    return (report.get("status") == "FAIL" and report.get("returncode") == 1
            and report.get("validation_error") is None and worker.get("status") == "FAIL"
            and worker.get("operation") == operation
            and (error_type is None or worker.get("error_type") == error_type)
            and text in worker.get("reason", ""))


def _effects(project: Path) -> list[str]:
    directory = project / ".bago/state/task-effects"
    return sorted(p.name for p in directory.glob("*.json")) if directory.is_dir() else []


def _demo_spiral(context, output: Path) -> dict:
    output = new_external_path(output, (context.SKILL.parent,))
    output.mkdir(parents=True)
    records, checks = {}, {}
    project = _new_project(context, output / "main", "spiral")
    records["init"] = _call(context, project, "spiral", "init")
    for cycle in (1, 2):
        records[f"cycle_{cycle}"] = _call(context, project, "spiral", "run")
    one, two = records["cycle_1"], records["cycle_2"]
    checks["actual_effect_and_independent_readback"] = all(
        item["status"] == "PASS" and len(item["independent_observations"]) == 1
        for item in (one, two))
    checks["restart_retains_phase_and_cycles"] = (
        one["worker"].get("state_observed", {}).get("cycles") == 1
        and two["worker"].get("state_observed", {}).get("cycles") == 2
        and two["worker"].get("state_observed", {}).get("phase") == 2
        and one["worker"].get("worker_pid") != two["worker"].get("worker_pid"))
    checks["twelve_steps_in_dependency_order"] = all(
        item["worker"].get("stages_observed") == ["OBSERVE", "DETECT", "PROPOSE", "SELECT", "ACT",
            "VALIDATE", "RECORD", "REFLECT", "EVOLVE", "REMEMBER", "DISTILL", "EMIT"]
        for item in (one, two))
    records["deactivate"] = _call(context, project, "spiral", "deactivate")
    before = _effects(project)
    records["inactive_run"] = _call(context, project, "spiral", "run")
    checks["inactive_agent_cannot_run"] = (records["deactivate"]["status"] == "PASS"
        and _negative(records["inactive_run"], "run", text="agent is inactive or missing")
        and before == _effects(project))
    records["outside_root_denial"] = _call(context, project, "spiral", "denied-effect")
    checks["gateway_rejects_outside_root"] = (_negative(records["outside_root_denial"], "denied-effect",
        "ExecutionGatewayError", "outside its trusted root")
        and not (output / "forbidden-outside-lab.json").exists())

    denied = _new_project(context, output / "gate-denial", "spiral")
    records["gate_init"] = _call(context, denied, "spiral", "init", "gate-denial")
    records["gate_run"] = _call(context, denied, "spiral", "run")
    blocked = records["gate_run"]["worker"].get("result", {}).get("state_vector", {}).get("blocked_skills")
    checks["closed_harmony_gate_has_no_denied_effect"] = (
        records["gate_init"]["status"] == "PASS" and _negative(records["gate_run"], "run")
        and blocked == ["fixture-denied"] and len(_effects(denied)) == 1
        and not any("fixture-denied" in p for p in _effects(denied)))

    broken = _new_project(context, output / "persistence-failure", "spiral")
    (broken / ".bago").write_text("controlled storage obstruction\n", encoding="utf-8")
    records["persistence_failure"] = _call(context, broken, "spiral", "init")
    checks["persistence_failure_is_visible"] = _negative(records["persistence_failure"], "init", "NotADirectoryError")
    return _finish_demo(context, output, "spiral", records, checks)


def _demo_adaptation(context, output: Path) -> dict:
    output = new_external_path(output, (context.SKILL.parent,))
    output.mkdir(parents=True)
    records, checks, projects = {}, {}, {}
    for mode in ("on", "off"):
        project = _new_project(context, output / mode, "adaptation", mode)
        projects[mode] = project
        records[f"{mode}_init"] = _call(context, project, "adaptation", "init")
        for cycle in range(1, 5):
            records[f"{mode}_{cycle}"] = _call(context, project, "adaptation", "cycle")
    checks["same_task_input_in_both_modes"] = _hash(projects["on"] / "fixture.json") == _hash(projects["off"] / "fixture.json")
    checks["all_eight_cycles_observed"] = all(records[f"{mode}_{cycle}"]["status"] == "PASS"
        for mode in ("on", "off") for cycle in range(1, 5))
    on_four, off_four = records["on_4"]["worker"], records["off_4"]["worker"]
    def goal(payload, name):
        return next((x for x in payload.get("outcomes", []) if x.get("goal") == name), {})
    checks["three_executed_failures_are_persisted"] = all(
        goal(records[f"on_{cycle}"]["worker"], "quick_check").get("observation", {}).get("success") is False
        for cycle in (1, 2, 3))
    checks["fresh_process_plan_and_act_change_only_with_learning"] = (
        goal(on_four, "quick_check").get("plan", {}).get("skip") is True
        and goal(on_four, "quick_check").get("action", {}).get("skipped") is True
        and goal(off_four, "quick_check").get("action", {}).get("skipped") is False
        and len({records[f"on_{cycle}"]["worker"].get("worker_pid") for cycle in range(1, 5)}) == 4)
    checks["physical_effect_counts_match_on_off"] = (
        sum(p.endswith("_health.json") for p in _effects(projects["on"])) == 3
        and sum(p.endswith("_health.json") for p in _effects(projects["off"])) == 4)
    checks["control_goal_remains_eligible"] = all(
        goal(records[f"{mode}_{cycle}"]["worker"], "summary").get("action", {}).get("skipped") is False
        for mode in ("on", "off") for cycle in range(1, 5))
    checks["off_mode_does_not_write_learning"] = not (projects["off"] / ".bago/state/auto_learnings.jsonl").exists()
    fresh = _new_project(context, output / "other-project", "adaptation")
    records["other_project"] = _call(context, fresh, "adaptation", "cycle")
    checks["other_project_does_not_inherit_skip"] = goal(records["other_project"]["worker"], "quick_check").get("action", {}).get("skipped") is False
    records["invalid_observation"] = _call(context, projects["on"], "adaptation", "invalid-observation")
    invalid = records["invalid_observation"]["worker"]
    checks["invalid_observation_rejected_without_write"] = (_negative(records["invalid_observation"],
        "invalid-observation", "ValueError", "success must be a boolean") and invalid.get("rejected") is True
        and invalid.get("observations_before") == invalid.get("observations_after"))
    broken = _new_project(context, output / "persistence-failure", "adaptation")
    (broken / ".bago").write_text("controlled storage obstruction\n", encoding="utf-8")
    records["persistence_failure"] = _call(context, broken, "adaptation", "failed-persistence")
    checks["persistence_failure_is_visible"] = _negative(records["persistence_failure"], "failed-persistence",
        "LearningPersistenceError", "could not be persisted")
    return _finish_demo(context, output, "adaptation", records, checks)


def _finish_demo(context, output, kind, records, checks):
    report = {"schema": "bago.suite.runtime-lab.demo.v1", "kind": kind,
              "status": "PASS" if checks and all(checks.values()) else "FAIL",
              "scope": SCOPE, "checks": checks, "identity": _identity(context),
              "records": {name: {"status": value["status"], "evidence": value["evidence"]}
                          for name, value in records.items()},
              "evidence": str(output / "DEMO_EVIDENCE.json"),
              "negative_cases": "explicit gate denial, invalid feedback and/or controlled real storage obstruction",
              "limits": ["fixture adapters only", "not native host agents", "not full legacy CLI",
                         "not live BAGO5/ADL", "not rollback of partial runtime effects",
                         "not crash-safe replay", "not general learning improvement", "Windows NOT_RUN"]}
    write_new_json(output / "DEMO_EVIDENCE.json", report)
    return report


def execute(args, context) -> dict:
    context = _context(context)
    context.SKILL = Path(context.SKILL).resolve()
    kind, action = args.command, args.runtime_action
    if not handles(args):
        raise ValueError("not a runtime laboratory command")
    if action == "demo":
        return (_demo_spiral if kind == "spiral" else _demo_adaptation)(context, args.output)
    if action == "init":
        project = _new_project(context, args.output, kind, getattr(args, "mode", "on"))
        return _call(context, project, kind, "init")
    return _call(context, args.project, kind, action)
