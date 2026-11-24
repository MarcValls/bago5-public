#!/usr/bin/env python3
"""
learning_writer.py — BAGO Aprendiz: cierra el loop de aprendizaje autónomo.

El aprendizaje en BAGO tiene dos capas:
  1. .bago/state/auto_learnings.jsonl  ← observaciones del loop autónomo
  2. .bago/knowledge/auto_patterns.md  ← patrones promovidos (≥3 ocurrencias)

El LearningWriter conecta el autonomous_loop con el sistema de memoria
distribuida existente (habit.py, project_memory.py, knowledge/).

Flujo:
  OBSERVE (autonomous_loop) → learner.observe(...)
      ↓
  auto_learnings.jsonl  (append-only, raw observations)
      ↓
  get_patterns()        → patrones con count ≥ threshold
      ↓
  auto_promote()        → knowledge/auto_patterns.md

Uso desde autonomous_loop:
    learner = LearningWriter(ctx)
    learner.observe(goal="quick_check", agent="VALIDADOR",
                    success=True, delta_health=5, signals=["health_improved"])
    context = learner.get_context_for_planning()  # feed to PLAN phase

Lives at: .bago/core/learning_writer.py
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bago_context import BagoContext

# ── Paths ──────────────────────────────────────────────────────────────────────
_THIS_FILE   = Path(__file__).resolve()
_BAGO_ROOT   = Path(os.environ.get("BAGO_PADRE_PATH") or _THIS_FILE.parents[2])
_STATE_DIR   = _BAGO_ROOT / ".bago" / "state"
_KNOWLEDGE   = _BAGO_ROOT / ".bago" / "knowledge"
_LEARNINGS   = _STATE_DIR  / "auto_learnings.jsonl"
_AUTO_PATTERNS = _KNOWLEDGE / "auto_patterns.md"

# ── Constants ──────────────────────────────────────────────────────────────────
PROMOTE_THRESHOLD = 3       # pattern seen ≥ N times → auto-promote
MAX_LEARNINGS     = 500     # rotate when file exceeds this many lines


class LearningPersistenceError(RuntimeError):
    """A learning observation or promotion could not be preserved faithfully."""


def _validate_observation(entry: Any) -> None:
    if not isinstance(entry, dict):
        raise ValueError("observation must be an object")
    for field in ("goal", "agent"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f"observation {field} must be non-empty text")
    if type(entry.get("success")) is not bool:
        raise ValueError("observation success must be a boolean")
    for field in ("signals", "tools_run"):
        values = entry.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"observation {field} must be a list of text values")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, text: str) -> None:
    """Replace a canonical promoted-learning artifact through its owner."""
    from bago_core.server_effects import write_learning_text

    write_learning_text(path, text, trusted_root=_BAGO_ROOT)


def _append_jsonl(path: Path, entry: dict) -> None:
    """Append one JSON line to a .jsonl file."""
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    from bago_core.server_effects import append_learning_text

    append_learning_text(path, line, trusted_root=_BAGO_ROOT)


def _read_learnings() -> list[dict]:
    """Read all observations from auto_learnings.jsonl."""
    if not _LEARNINGS.exists():
        return []
    entries: list[dict] = []
    for line_number, line in enumerate(_LEARNINGS.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            _validate_observation(entry)
        except (json.JSONDecodeError, ValueError) as exc:
            raise LearningPersistenceError(
                f"invalid learning observation at line {line_number} of {_LEARNINGS}"
            ) from exc
        entries.append(entry)
    return entries


def _rotate_if_needed() -> None:
    """Keep auto_learnings.jsonl under MAX_LEARNINGS lines."""
    if not _LEARNINGS.exists():
        return
    entries = _read_learnings()
    if len(entries) > MAX_LEARNINGS:
        # Keep the most recent MAX_LEARNINGS entries
        trimmed = entries[-MAX_LEARNINGS:]
        _atomic_write(_LEARNINGS, "\n".join(json.dumps(e, ensure_ascii=False) for e in trimmed) + "\n")


# ── LearningWriter ─────────────────────────────────────────────────────────────

class LearningWriter:
    """
    Observes autonomous cycle outcomes, detects recurring patterns,
    and promotes validated patterns to .bago/knowledge/auto_patterns.md.

    Thread-safe for single-process use. Not safe for concurrent writers.
    """

    def __init__(self, ctx: "BagoContext | None" = None) -> None:
        self._ctx = ctx

    # ── Public API ─────────────────────────────────────────────────────────────

    def observe(
        self,
        goal:         str,
        agent:        str,
        success:      bool,
        delta_health: int   = 0,
        signals:      list  = None,
        tools_run:    list  = None,
        cycle:        int   = 0,
        notes:        str   = "",
    ) -> None:
        """
        Record one observation from an autonomous cycle.

        Called from AutonomousLoop.observe() after each goal is executed.
        Checks whether a pattern threshold has been reached and auto-promotes.
        Persistence errors propagate. An observation already appended is not
        rolled back if subsequent retention or promotion fails.
        """
        entry: dict[str, Any] = {
            "ts":           _now(),
            "goal":         goal,
            "agent":        agent,
            "success":      success,
            "delta_health": delta_health,
            "signals":      signals or [],
            "tools_run":    tools_run or [],
            "cycle":        cycle,
            "notes":        notes,
        }
        _validate_observation(entry)
        try:
            _append_jsonl(_LEARNINGS, entry)
        except Exception as exc:
            raise LearningPersistenceError(
                f"learning observation could not be persisted to {_LEARNINGS}"
            ) from exc
        try:
            _rotate_if_needed()
        except Exception as exc:
            raise LearningPersistenceError(
                f"learning observation saved; retention failed for {_LEARNINGS}"
            ) from exc

        # Check for auto-promote opportunity
        try:
            self._maybe_promote(goal, agent, success)
        except Exception as exc:
            raise LearningPersistenceError(
                f"learning observation saved; pattern promotion failed for {_AUTO_PATTERNS}"
            ) from exc

        if self._ctx:
            self._ctx.log("info",
                f"learning: [{agent}] {goal} → {'ok' if success else 'fail'}"
                + (f" Δhealth={delta_health:+d}" if delta_health else ""),
                tool="learner")

    def get_patterns(self, min_count: int = PROMOTE_THRESHOLD) -> list[dict]:
        """
        Return patterns seen ≥ min_count times.
        A pattern is a (goal, agent, success) triple.
        """
        entries = _read_learnings()
        counter: Counter = Counter()
        for e in entries:
            key = (e.get("goal", ""), e.get("agent", ""), e.get("success", False))
            counter[key] += 1

        result = []
        for (goal, agent, success), count in counter.most_common():
            if count >= min_count:
                result.append({
                    "goal": goal, "agent": agent, "success": success,
                    "count": count,
                    "pattern_id": f"{agent}:{goal}:{'ok' if success else 'fail'}",
                })
        return result

    def get_context_for_planning(self) -> dict:
        """
        Return accumulated insights to feed into the PLAN phase.

        Returns a dict with:
          skip_goals:   set of goals that consistently fail (avoid them)
          effective:    {goal: agent} pairs that consistently succeed
          signals:      most common signals from recent cycles
        """
        entries = _read_learnings()
        if not entries:
            return {"skip_goals": set(), "effective": {}, "signals": []}

        # Consider only recent 50 entries
        recent = entries[-50:]

        fail_count:    Counter = Counter()
        success_count: Counter = Counter()
        signal_count:  Counter = Counter()

        for e in recent:
            goal = e.get("goal", "")
            if e.get("success"):
                success_count[goal] += 1
            else:
                fail_count[goal] += 1
            for sig in e.get("signals", []):
                signal_count[sig] += 1

        # Skip goals that fail consistently (fail >= 3, success < 1)
        skip_goals: set = {
            g for g in fail_count
            if fail_count[g] >= 3 and success_count.get(g, 0) == 0
        }

        # Effective: goals with success rate >= 70%
        effective: dict = {}
        for g in success_count:
            total = success_count[g] + fail_count.get(g, 0)
            if total >= 2 and success_count[g] / total >= 0.7:
                # Find most recent agent for this goal
                for e in reversed(recent):
                    if e.get("goal") == g and e.get("success"):
                        effective[g] = e.get("agent", "")
                        break

        signals = [s for s, _ in signal_count.most_common(10)]

        return {"skip_goals": skip_goals, "effective": effective, "signals": signals}

    def get_summary(self) -> dict:
        """Human-readable summary of accumulated learnings."""
        entries = _read_learnings()
        if not entries:
            return {"total": 0, "patterns": [], "promoted_count": self._count_promoted()}

        total = len(entries)
        recent = entries[-20:]
        success_rate = sum(1 for e in recent if e.get("success")) / len(recent) if recent else 0

        return {
            "total":        total,
            "recent_sr":    round(success_rate, 2),
            "patterns":     self.get_patterns(),
            "promoted_count": self._count_promoted(),
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _maybe_promote(self, goal: str, agent: str, success: bool) -> None:
        """Check if (goal, agent, success) has hit the promote threshold."""
        if not success:
            return  # only promote successful patterns
        entries = _read_learnings()
        pattern_key = (goal, agent, True)
        count = sum(
            1 for e in entries
            if (e.get("goal"), e.get("agent"), e.get("success")) == pattern_key
        )
        # Retry a previously failed promotion; auto_promote is idempotent.
        if count >= PROMOTE_THRESHOLD:
            self.auto_promote(goal, agent, count)

    def auto_promote(self, goal: str, agent: str, count: int) -> bool:
        """
        Promote a validated pattern to .bago/knowledge/auto_patterns.md.
        Avoids duplicate entries.
        """
        pattern_id = f"{agent}:{goal}:ok"

        # Check if already promoted
        existing = ""
        if _AUTO_PATTERNS.exists():
            existing = _AUTO_PATTERNS.read_text(encoding="utf-8")
            if f"## PATTERN: {pattern_id}" in existing.splitlines():
                return False  # already promoted

        # Build new entry
        entry_md = (
            f"\n## PATTERN: {pattern_id}\n\n"
            f"- **Agent:** {agent}\n"
            f"- **Goal:** {goal}\n"
            f"- **Outcome:** ✅ success\n"
            f"- **Count:** {count} confirmed occurrences\n"
            f"- **Promoted:** {_now()[:10]}\n"
            f"- **Source:** autonomous_loop auto-observe\n\n"
            f"> Pattern: `{agent}` ejecutando `{goal}` tiene tasa de éxito confirmada.\n"
            f"> El planificador autónomo puede priorizar esta combinación.\n"
        )

        # Replace the whole document atomically: a failed append could leave
        # a partial heading that a later attempt mistakes for a promotion.
        if not _AUTO_PATTERNS.exists():
            header = (
                "# Auto-Patterns — BAGO Autonomous Learning\n\n"
                "> Patrones promovidos automáticamente por el loop autónomo.\n"
                "> Umbral: 3 ocurrencias exitosas confirmadas.\n"
                "> No editar manualmente — añadir contexto en project_patterns.md.\n\n"
            )
            _atomic_write(_AUTO_PATTERNS, header + entry_md)
        else:
            _atomic_write(_AUTO_PATTERNS, existing + entry_md)

        if self._ctx:
            self._ctx.log("info",
                f"learning: AUTO-PROMOTED pattern {pattern_id} (count={count})",
                tool="learner")
            self._ctx.emit("learning:promoted", {
                "pattern_id": pattern_id, "goal": goal, "agent": agent,
                "count": count, "ts": _now(),
            })
        return True

    def _count_promoted(self) -> int:
        if not _AUTO_PATTERNS.exists():
            return 0
        return _AUTO_PATTERNS.read_text(encoding="utf-8").count("## PATTERN:")
