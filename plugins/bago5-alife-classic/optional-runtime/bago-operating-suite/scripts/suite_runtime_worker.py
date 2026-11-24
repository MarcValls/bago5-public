"""One isolated process for the Suite's explicit, bounded runtime laboratory.

The historical runtime is imported unchanged. The fixture adapters below replace
only its tool/skill dispatch seam; planning, observation, agent lifecycle and the
server-owned ExecutionGateway remain the actual bundled implementations.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from suite_safety import read_json, reject_links

SCHEMA = "bago.suite.runtime-lab.v1"
STEPS = ["OBSERVE", "DETECT", "PROPOSE", "SELECT", "ACT", "VALIDATE",
         "RECORD", "REFLECT", "EVOLVE", "REMEMBER", "DISTILL", "EMIT"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_project(project: Path, kind: str) -> dict:
    reject_links(project)
    marker = read_json(project / "RUNTIME_LAB.json", max_bytes=64000)
    if (not isinstance(marker, dict) or marker.get("schema") != SCHEMA
            or marker.get("kind") != kind or marker.get("project") != str(project)
            or marker.get("mode") not in {"on", "off"}):
        raise ValueError("lab identity, project binding or mode is invalid")
    return marker


def setup(skill: Path, project: Path) -> None:
    backend = skill / "runtime/BAGO-4.11.10/backend"
    sys.path[:0] = [str(backend), str(backend / ".bago/core"), str(backend / ".bago/tools")]
    os.environ.update({
        "BAGO_USER_ROOT": str(project / "user"),
        "BAGO_STATE_ROOT": str(project / "user/state"),
        "BAGO_RUNTIME_ROOT": str(project / "user/runtime"),
        "BAGO_WORKSPACE_ROOT": str(project), "BAGO_SCAN_ROOT": str(project),
        "BAGO_PADRE_PATH": str(project), "BAGO_AUTO_DELEGATE": "0",
        "BAGO_ORCHESTRATE": "0", "OTEL_SDK_DISABLED": "true",
    })


def governed_json(project: Path, path: Path, payload: dict) -> dict:
    from bago_core.server_effects import write_text_atomic
    reject_links(path)
    receipt = write_text_atomic(
        path, json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        trusted_root=project, source_surface="suite.runtime-lab", session_id="suite-runtime-lab",
    )
    observed = read_json(path)
    if receipt.get("ok") is not True or observed != payload:
        raise RuntimeError("governed effect receipt/readback mismatch")
    return {"receipt": receipt, "path": path.relative_to(project).as_posix(),
            "sha256": digest(path), "observed": observed}


def fixture_task(project: Path, invocation: str, tool: str) -> dict:
    """A real bounded data transformation; its output is independently inspectable."""
    if tool not in {"health", "dashboard", "fixture-summary", "fixture-denied"}:
        raise ValueError("tool is outside the explicit fixture adapter")
    data = read_json(project / "fixture.json", max_bytes=64000)
    values, limit = data.get("values"), data.get("limit")
    if (not isinstance(values, list) or not values or len(values) > 100
            or any(type(v) is not int or abs(v) > 1000000 for v in values)
            or type(limit) is not int):
        raise ValueError("fixture requires bounded integer values and an integer limit")
    summary = {"count": len(values), "sum": sum(values),
               "within_limit": sum(values) <= limit, "input_sha256": digest(project / "fixture.json")}
    target = project / ".bago/state/task-effects" / f"{invocation}_{tool}.json"
    effect = governed_json(project, target, summary)
    return {"tool": tool, "returncode": 1 if tool == "health" and not summary["within_limit"] else 0,
            "effect": effect}


def spiral_operation(project: Path, operation: str, invocation: str, scenario: str) -> dict:
    import spiral_agent as spiral
    spiral.configure_paths(str(project))
    if operation == "init":
        registry = {"fixture-summary": {"phase": 6 if scenario == "gate-denial" else 0}}
        if scenario == "gate-denial":
            registry["fixture-denied"] = {"phase": 0}
        governed_json(project, project / ".bago/state/skill_registry.json", registry)
        governed_json(project, project / ".bago/state/global_state.json", {"health_score": {"score": 100}})
        code = spiral.main(["--root", str(project), "spawn", "suite-fixture", "--skills", ",".join(registry)])
        if code:
            raise RuntimeError("spiral spawn did not complete")
        return {"status": "PASS", "agent_id": "suite-fixture", "registry": spiral.load_agents_registry()}
    if operation == "inspect":
        return {"status": "PASS", "agents": spiral.list_agents()}
    if operation == "deactivate":
        code = spiral.main(["--root", str(project), "kill", "suite-fixture"])
        if code:
            raise RuntimeError("spiral deactivation did not complete")
        return {"status": "PASS", "agents": spiral.list_agents()}
    if operation != "run":
        raise ValueError("unsupported spiral operation")
    agent = spiral.agent_from_registry("suite-fixture")
    if agent is None:
        return {"status": "FAIL", "reason": "agent is inactive or missing", "effects": []}
    native_run_skill = spiral.run_skill
    effects, stages = [], []

    def fixture_dispatch(skill_id):
        if skill_id not in {"fixture-summary", "fixture-denied"}:
            raise ValueError("skill is outside the explicit fixture adapter")
        native = native_run_skill(skill_id)
        # The native skill engine tracks its own cycle. Its radius is a heuristic,
        # so successful task execution is checked separately below.
        if native.validate == "FAIL":
            return native
        state = read_json(project / ".bago/state/skills" / f"{skill_id}.json")
        if len(state.get("cycles", [])) != native.state_vector.get("cycles"):
            raise RuntimeError("native skill state was not persisted")
        effect = fixture_task(project, invocation, skill_id)
        effects.append(effect)
        return spiral.SkillResult(
            skill_id=skill_id, radius_gained=native.radius_gained,
            validate="GO" if effect["returncode"] == 0 else "FAIL",
            fingerprint=native.fingerprint + ["suite-fixture-effect-observed"],
            state_vector={**native.state_vector, "task_effect": effect["effect"]["path"]},
        )

    spiral.run_skill = fixture_dispatch
    for stage in STEPS:
        name = "_step_" + stage.lower()
        original = getattr(agent, name)

        def traced(context, _original=original, _stage=stage):
            stages.append(_stage)
            return _original(context)
        setattr(agent, name, traced)
    result = agent.run().to_dict()
    state = read_json(project / ".bago/state/agents/suite-fixture/state.json")
    episodes = read_json(project / ".bago/state/agents/suite-fixture/episodic.json")
    return {"status": "PASS" if result["validate"] == "GO" and stages == STEPS else "FAIL",
            "result": result, "stages_observed": stages, "effects": effects,
            "state_observed": state, "episodes_observed": episodes,
            "adapter": "native skill bookkeeping plus explicit fixture data-summary effect",
            "radius_is_not_task_metric": True}


def adaptation_operation(project: Path, operation: str, invocation: str, mode: str) -> dict:
    import autonomous_loop as runtime
    from learning_writer import LearningWriter
    writer = LearningWriter()
    if operation == "init":
        return {"status": "PASS", "mode": mode, "observations": 0}
    if operation == "inspect":
        context = writer.get_context_for_planning()
        context["skip_goals"] = sorted(context["skip_goals"])
        return {"status": "PASS", "mode": mode, "summary": writer.get_summary(), "planning_context": context}
    if operation == "invalid-observation":
        before = writer.get_summary()["total"]
        try:
            writer.observe("quick_check", "VALIDADOR", "false")
        except ValueError as exc:
            return {"status": "FAIL", "rejected": True, "reason": str(exc),
                    "error_type": type(exc).__name__,
                    "observations_before": before, "observations_after": writer.get_summary()["total"]}
        return {"status": "PASS", "rejected": False}
    if operation == "failed-persistence":
        writer.observe("quick_check", "VALIDADOR", False)
        return {"status": "PASS", "unexpected_persistence_success": True}
    if operation != "cycle":
        raise ValueError("unsupported adaptation operation")

    class BoundLabLoop(runtime.AutonomousLoop):
        def __init__(self):
            # The fixture supplies observation and tool adapters; constructing the
            # host context/inbox would incorrectly inspect the ambient installation.
            self.learner = writer if mode == "on" else None
            self.unsafe = False
            self.dry_run = False
            self.verbose = False
            self.ctx = None
            self._cycle_history = []

    loop = BoundLabLoop()
    calls = []

    def fixture_tool(tool, **kwargs):
        if kwargs.get("mutating") or kwargs.get("unsafe"):
            raise ValueError("lab does not authorize arbitrary mutating tools")
        result = fixture_task(project, invocation, tool)
        calls.append(result)
        return result["returncode"], json.dumps(result["effect"]["observed"], sort_keys=True)

    runtime._run_tool = fixture_tool
    state = {"pack_ok": True, "health": 70, "stale_count": 0, "inbox_tasks": []}
    plan = loop.plan(state)
    outcomes = []
    for goal in plan:
        action = loop.act(goal)
        observation = loop.observe(goal, action, state, state)
        outcomes.append({"goal": goal["goal"], "plan": goal, "action": action, "observation": observation})
    context = writer.get_context_for_planning()
    context["skip_goals"] = sorted(context["skip_goals"])
    return {"status": "PASS", "mode": mode, "outcomes": outcomes, "effects": calls,
            "summary": writer.get_summary(), "planning_context": context,
            "adapter": "native plan/act/observe with explicit health/dashboard fixture adapters",
            "scope": "three failed quick_check observations cause a bounded skip; no general improvement claim"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True, type=Path)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--kind", choices=("spiral", "adaptation"), required=True)
    parser.add_argument("--operation", required=True)
    parser.add_argument("--invocation", required=True)
    parser.add_argument("--scenario", choices=("normal", "gate-denial"), default="normal")
    args = parser.parse_args()
    captured = io.StringIO()
    result = {}
    try:
        if len(args.invocation) != 32 or any(c not in "0123456789abcdef" for c in args.invocation):
            raise ValueError("invalid invocation identity")
        reject_links(args.project)
        reject_links(args.skill)
        project, skill = args.project.resolve(strict=True), args.skill.resolve(strict=True)
        marker = checked_project(project, args.kind)
        setup(skill, project)
        with contextlib.redirect_stdout(captured):
            if args.operation == "denied-effect":
                from bago_core.server_effects import write_text_atomic
                write_text_atomic(project.parent / "forbidden-outside-lab.json", "forbidden",
                                  trusted_root=project, source_surface="suite.runtime-lab",
                                  session_id="suite-runtime-lab")
                result = {"status": "PASS", "unexpected_effect": True}
            elif args.kind == "spiral":
                result = spiral_operation(project, args.operation, args.invocation, args.scenario)
            else:
                result = adaptation_operation(project, args.operation, args.invocation, marker["mode"])
    except Exception as exc:
        result = {"status": "FAIL", "reason": f"{type(exc).__name__}: {exc}",
                  "error_type": type(exc).__name__, "error_code": getattr(exc, "code", None),
                  "partial_effects_possible": True}
    result.update({"invocation": args.invocation, "operation": args.operation,
                   "project": str(args.project), "worker_pid": os.getpid(),
                   "runtime_stdout": captured.getvalue()[-8000:]})
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
