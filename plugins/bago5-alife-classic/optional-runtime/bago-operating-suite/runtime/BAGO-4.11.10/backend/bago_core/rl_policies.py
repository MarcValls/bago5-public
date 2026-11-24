from __future__ import annotations

import json
import hashlib
import math
from numbers import Integral
from pathlib import Path

from bago_core.user_state_paths import state_root
from typing import Any

try:
    import numpy as np
except Exception:
    np = None  # type: ignore[assignment]

def numpy_available() -> bool:
    return np is not None

def _require_numpy() -> Any:
    if np is None:
        raise RuntimeError("numpy not installed; RL policy layer disabled")
    return np

class LinUCBPolicy:
    def __init__(self, n_actions: int, n_features: int, alpha: float = 1.0):
        npx = _require_numpy()
        self.n_actions = n_actions
        self.n_features = n_features
        self.alpha = alpha
        self.A = [npx.eye(n_features) for _ in range(n_actions)]
        self.b = [npx.zeros(n_features) for _ in range(n_actions)]
        self.thetas = [npx.zeros(n_features) for _ in range(n_actions)]
        self._update_all()

    def _update_all(self) -> None:
        npx = _require_numpy()
        for action in range(self.n_actions):
            try:
                self.thetas[action] = npx.linalg.solve(self.A[action], self.b[action])
            except npx.linalg.LinAlgError:
                self.thetas[action] = npx.zeros(self.n_features)

    def select(self, features: Any) -> int:
        npx = _require_numpy()
        x = npx.asarray(features, dtype=float)
        scores = []
        for action in range(self.n_actions):
            theta = self.thetas[action]
            inv_a = npx.linalg.inv(self.A[action])
            score = theta @ x + self.alpha * npx.sqrt(x @ inv_a @ x)
            scores.append(score)
        return int(npx.argmax(scores))

    def update(self, action: int, features: Any, reward: float) -> None:
        npx = _require_numpy()
        x = npx.asarray(features, dtype=float)
        self.A[action] += npx.outer(x, x)
        self.b[action] += float(reward) * x
        self._update_all()

class BCPolicy:
    def __init__(self, n_actions: int, n_features: int, lr: float = 0.01):
        npx = _require_numpy()
        if any(isinstance(value, bool) or not isinstance(value, Integral) or value <= 0
               for value in (n_actions, n_features)):
            raise ValueError("policy dimensions must be positive integers")
        if not math.isfinite(float(lr)) or float(lr) <= 0:
            raise ValueError("policy learning rate must be finite and positive")
        self.n_actions = int(n_actions)
        self.n_features = int(n_features)
        self.lr = float(lr)
        self.W = npx.zeros((n_actions, n_features))
        self.bias = npx.zeros(n_actions)
        self.training_feature_hashes: list[str] | None = None
        self.training_action_counts: list[int] | None = None

    def _features(self, features: Any) -> Any:
        npx = _require_numpy()
        x = npx.asarray(features, dtype=float)
        if x.shape != (self.n_features,) or not npx.isfinite(x).all():
            raise ValueError("policy features must have the expected shape and finite values")
        return x

    def _softmax(self, values: Any) -> Any:
        npx = _require_numpy()
        arr = npx.asarray(values, dtype=float)
        if not npx.isfinite(arr).all():
            raise ValueError("policy logits must be finite")
        e = npx.exp(arr - npx.max(arr))
        return e / e.sum()

    def predict(self, features: Any) -> int:
        npx = _require_numpy()
        x = self._features(features)
        logits = self.W @ x + self.bias
        probs = self._softmax(logits)
        return int(npx.argmax(probs))

    def train_step(self, features: Any, action: int, reward: float) -> float:
        npx = _require_numpy()
        x = self._features(features)
        if isinstance(action, bool) or not isinstance(action, Integral) or not 0 <= action < self.n_actions:
            raise ValueError("policy action must be an in-range integer")
        if not math.isfinite(float(reward)):
            raise ValueError("policy reward must be finite")
        logits = self.W @ x + self.bias
        probs = self._softmax(logits)
        target = npx.zeros(self.n_actions)
        target[action] = 1.0
        grad = (probs - target) * float(reward)
        updated_W = self.W - self.lr * npx.outer(grad, x)
        updated_bias = self.bias - self.lr * grad
        loss = float(-npx.log(max(probs[action], 1e-8)) * float(reward))
        if not npx.isfinite(updated_W).all() or not npx.isfinite(updated_bias).all() or not math.isfinite(loss):
            raise ValueError("policy update produced non-finite parameters or loss")
        self.W, self.bias = updated_W, updated_bias
        # A direct update after load changes the training population. Its old
        # split metadata cannot justify a new held-out claim. The batch trainer
        # rebuilds these fields only after every sample has been processed.
        self.training_feature_hashes = None
        self.training_action_counts = None
        return loss

    def save(self, path: Path) -> None:
        from bago_core.server_effects import write_text_atomic

        payload = {
            "n_actions": self.n_actions,
            "n_features": self.n_features,
            "lr": self.lr,
            "W": self.W.tolist(),
            "bias": self.bias.tolist(),
            "training_feature_hashes": self.training_feature_hashes,
            "training_action_counts": self.training_action_counts,
        }
        write_text_atomic(
            path,
            json.dumps(payload, indent=2, ensure_ascii=False),
            trusted_root=state_root(),
            source_surface="rl.bc_policy",
            session_id="rl-bc-policy",
        )

    @classmethod
    def load(cls, path: Path) -> "BCPolicy":
        npx = _require_numpy()
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("saved policy must be an object")
        policy = cls(data["n_actions"], data["n_features"], data.get("lr", 0.01))
        policy.W = npx.asarray(data["W"], dtype=float)
        policy.bias = npx.asarray(data["bias"], dtype=float)
        if policy.W.shape != (policy.n_actions, policy.n_features) or policy.bias.shape != (policy.n_actions,):
            raise ValueError("saved policy parameter shape does not match dimensions")
        if not npx.isfinite(policy.W).all() or not npx.isfinite(policy.bias).all():
            raise ValueError("saved policy parameters must be finite")
        hashes = data.get("training_feature_hashes")
        counts = data.get("training_action_counts")
        if hashes is not None and (not isinstance(hashes, list) or any(
                not isinstance(item, str) or len(item) != 64 or any(c not in "0123456789abcdef" for c in item)
                for item in hashes)):
            raise ValueError("saved policy training fingerprints are invalid")
        if counts is not None and (not isinstance(counts, list) or len(counts) != policy.n_actions
                or any(type(item) is not int or item < 0 for item in counts) or sum(counts) == 0):
            raise ValueError("saved policy training class counts are invalid")
        policy.training_feature_hashes = hashes
        policy.training_action_counts = counts
        return policy


def _feature_fingerprint(features: list[float]) -> str:
    # Signed zero is the same model input and must not bypass split checks.
    encoded = json.dumps([0.0 if float(value) == 0.0 else float(value) for value in features],
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def policy_dir(base_path: str | Path) -> Path:
    return state_root() / "rl_policies"

def bc_policy_path(base_path: str | Path) -> Path:
    return policy_dir(base_path) / "bc_policy.json"

def _transition_log(base_path: str | Path) -> Path:
    return state_root() / "rl_transitions.jsonl"

def load_transition_samples(base_path: str | Path, n_features: int) -> list[tuple[list[float], int, float]]:
    path = _transition_log(base_path)
    if not path.exists():
        return []
    samples: list[tuple[list[float], int, float]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        features = event.get("features")
        action = event.get("action")
        reward = event.get("reward", 1.0)
        if not isinstance(features, list) or len(features) != n_features:
            continue
        if type(action) is not int:
            continue
        try:
            vector, weight = [float(v) for v in features], float(reward)
            if all(math.isfinite(value) for value in vector) and math.isfinite(weight):
                samples.append((vector, action, weight))
        except (TypeError, ValueError, OverflowError):
            continue
    return samples

# ---------------------------------------------------------------------------
# Auto-ingesta de transiciones desde el historial real del usuario.
# Misma fuente que la autoevolucion del clasificador de intenciones:
# convierte cada mensaje del usuario en una transicion (features, action, reward)
# para poder entrenar una politica BC sin requerir interacciones en vivo.
# Capa shadow: nunca ejecuta acciones, solo aprende a recomendar.
# ---------------------------------------------------------------------------

# Orden de acciones = intenciones del clasificador
INTENT_ACTIONS: list[str] = ["chat", "review", "execute", "work"]
ACTION_INDEX: dict[str, int] = {name: i for i, name in enumerate(INTENT_ACTIONS)}

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "chat": ["hola", "hey", "saludos", "continua", "gracias", "adios", "bago",
             "bago next", "bago start", "espanol", "hello", "hi"],
    "review": ["revisa", "mira", "reune", "busca", "chequea", "examina", "verifica",
               "analiza esto", "mira esto", "mira ahora", "list_directory",
               "read_file", "dame el contenido"],
    "execute": ["ejecuta", "corre", "lanza", "dispara", "run", "execute",
                "corre el comando", "ejecuta el script", "corre el script"],
    "work": ["trabaja", "modulariza", "adapta", "crea", "modifica", "refactoriza",
             "estructurala", "ordena", "desarrolla", "implementa", "construye",
             "genera", "haz que", "hazme", "adaptalo", "modularizala",
             "estructuralo", "organiza"],
}

_PATH_TOKENS = (":\\", "/", "\\", ".py", ".js", ".md", ".json", ".ps1")

def classify_message(message: str) -> str:
    """Clasifica un mensaje en una intencion (mirror de intent_engine, autocontenido)."""
    msg = message.lower().strip()
    for intent, words in _INTENT_KEYWORDS.items():
        if any(w in msg for w in words):
            return intent
    if len(msg) < 40 and not any(t in msg for t in _PATH_TOKENS):
        return "chat"
    return "work"

def message_features(message: str) -> list[float]:
    """Vector de features determinista (4 dims) a partir del mensaje."""
    msg = message.lower()
    f_len = min(len(message) / 200.0, 1.0)
    f_path = 1.0 if any(t in msg for t in _PATH_TOKENS) else 0.0
    f_exec = 1.0 if any(w in msg for w in _INTENT_KEYWORDS["execute"]) else 0.0
    f_question = 1.0 if (msg.strip().endswith("?") or msg.strip().startswith(
        ("que", "que", "como", "como", "por que", "por que", "cuando", "cuando", "donde", "donde"))) else 0.0
    return [f_len, f_path, f_exec, f_question]

def synthesize_transitions_from_history(base_path: str | Path, n_features: int = 4, limit: int = 4000) -> int:
    """Genera transiciones BC desde el historial de sesiones (~/.copilot/session-store.db)
    y las escribe en el log de transiciones. Devuelve el numero de transiciones anadidas.
    Solo escribe si el log esta vacio/inexistente (evita duplicar en cada entrenamiento)."""
    import sqlite3

    if n_features != 4:
        return 0  # las features sintetizadas son de dimension 4

    log_path = _transition_log(base_path)
    if log_path.exists() and log_path.stat().st_size > 0:
        return 0

    store_db = Path.home() / ".copilot" / "session-store.db"
    if not store_db.exists():
        return 0

    try:
        conn = sqlite3.connect(f"{store_db.as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT user_message FROM turns "
            "WHERE user_message IS NOT NULL AND user_message != '' "
            "AND LENGTH(user_message) < 800"
        )
        rows = cur.fetchall()
        conn.close()
    except Exception:
        return 0

    seen: set[str] = set()
    events: list[dict[str, Any]] = []
    for row in rows:
        msg = row["user_message"]
        if not msg or "══" in msg or "┌-" in msg or len(msg) > 400:
            continue
        if msg in seen:
            continue
        seen.add(msg)
        intent = classify_message(msg)
        events.append({
            "kind": "intent_sample",
            "source": "history",
            "features": message_features(msg),
            "action": ACTION_INDEX[intent],
            "reward": 1.0,
            "intent": intent,
        })
        if len(events) >= limit:
            break

    if not events:
        return 0

    from bago_core.server_effects import append_text_durable

    append_text_durable(
        log_path,
        "".join(json.dumps(ev, ensure_ascii=False) + "\n" for ev in events),
        trusted_root=state_root(),
        source_surface="rl.transitions.history",
        session_id="rl-transition-history",
    )
    return len(events)

def train_bc_policy(base_path: str | Path, n_actions: int, n_features: int, *,
                    allow_history_fallback: bool = True) -> dict[str, Any]:
    if not numpy_available():
        return {"status": "disabled", "reason": "numpy not installed", "can_execute": False}
    policy = BCPolicy(n_actions, n_features)
    samples = load_transition_samples(base_path, n_features)
    source = "transition_log"
    if not samples and allow_history_fallback:
        # Autoevolucion: si no hay transiciones en vivo, aprender del historial real.
        ingested = synthesize_transitions_from_history(base_path, n_features)
        if ingested:
            samples = load_transition_samples(base_path, n_features)
            source = "history"
    samples = [sample for sample in samples if 0 <= sample[1] < n_actions]
    if not samples:
        return {
            "status": "no_samples",
            "samples": 0,
            "policy_file": str(bc_policy_path(base_path)),
            "can_execute": False,
        }
    losses = []
    for features, action, reward in samples:
        losses.append(policy.train_step(features, action, reward))
    policy.training_feature_hashes = sorted({_feature_fingerprint(features) for features, _, _ in samples})
    policy.training_action_counts = [sum(action == i for _, action, _ in samples) for i in range(n_actions)]
    policy.save(bc_policy_path(base_path))
    return {
        "status": "trained",
        "source": source,
        "samples": len(losses),
        "loss": float(sum(losses) / len(losses)) if losses else 0.0,
        "policy_file": str(bc_policy_path(base_path)),
        "can_execute": False,
        "training_mode": "rebuild_from_available_samples",
        "improvement": "NOT_EVALUATED",
    }

def bc_policy_status(base_path: str | Path, n_features: int = 4) -> dict[str, Any]:
    """Return a read-only summary for the Laboratory UI."""
    policy_path = bc_policy_path(base_path)
    samples = load_transition_samples(base_path, n_features)
    return {
        "numpy_available": numpy_available(),
        "samples": len(samples),
        "policy_exists": policy_path.is_file(),
        "policy_file": str(policy_path),
        "actions": list(INTENT_ACTIONS),
        "can_execute": False,
    }


def eval_bc_policy(base_path: str | Path, n_features: int, *,
                   evaluation_samples: list[tuple[list[float], int]] | None = None) -> dict[str, Any]:
    """Probe availability or measure caller-supplied samples absent from training.

    A successful probe is not evidence of useful learning. Held-out results only
    describe the supplied labelled dataset, never overall system improvement.
    """
    if not numpy_available():
        return {"status": "disabled", "reason": "numpy not installed", "can_execute": False}
    path = bc_policy_path(base_path)
    if not path.exists():
        return {"status": "no_policy", "policy_file": str(path), "can_execute": False}
    policy = BCPolicy.load(path)
    if policy.n_features != n_features:
        raise ValueError("evaluation feature count does not match the saved policy")
    if evaluation_samples is not None:
        if not evaluation_samples:
            raise ValueError("evaluation samples must not be empty")
        if not policy.training_feature_hashes or not policy.training_action_counts:
            raise ValueError("training provenance unavailable; held-out evaluation cannot be established")
        training_hashes = set(policy.training_feature_hashes)
        checked = []
        for features, action in evaluation_samples:
            vector = policy._features(features).tolist()
            if isinstance(action, bool) or not isinstance(action, Integral) or not 0 <= action < policy.n_actions:
                raise ValueError("evaluation action must be an in-range integer")
            if _feature_fingerprint(vector) in training_hashes:
                raise ValueError("evaluation features overlap training samples")
            checked.append((vector, int(action)))
        baseline_action = max(range(policy.n_actions), key=policy.training_action_counts.__getitem__)
        correct = sum(policy.predict(features) == action for features, action in checked)
        baseline_correct = sum(action == baseline_action for _, action in checked)
        return {
            "status": "evaluated", "scope": "caller_supplied_held_out_samples",
            "policy_file": str(path), "samples": len(checked), "correct": correct,
            "accuracy": correct / len(checked),
            "baseline": "training_majority_class", "baseline_action": baseline_action,
            "baseline_correct": baseline_correct, "baseline_accuracy": baseline_correct / len(checked),
            "accuracy_delta": (correct - baseline_correct) / len(checked),
            "general_improvement_claim": False, "can_execute": False,
        }
    prediction = policy.predict([0.0 for _ in range(n_features)])
    return {
        "status": "ok",
        "scope": "prediction_probe_only",
        "improvement": "NOT_EVALUATED",
        "policy_file": str(path),
        "prediction_for_zero_vector": prediction,
        "can_execute": False,
    }

def render_policy_report(report: dict[str, Any], title: str) -> str:
    lines = [title, "-" * 40]
    for key, value in report.items():
        lines.append(f"{key:12}: {value}")
    lines.append("rule        : policy layer never executes actions directly")
    return "\n".join(lines)
