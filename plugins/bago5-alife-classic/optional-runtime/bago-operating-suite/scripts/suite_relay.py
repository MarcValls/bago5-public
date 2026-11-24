"""Cooperative serial agent relay inside the existing TaskStore ledger.

This module is not a second orchestrator. Host identities and external effects
remain outside its authority. A lease fences cooperative ledger operations,
not arbitrary OS processes. No prompt/context text is executed by this module.
"""
from __future__ import annotations

import hmac
import os
import secrets
import time
import uuid
from pathlib import Path

# Imported lazily by suite_control after its types and helpers are defined.
from suite_control import (ControlError, _bytes, _hash, _id, _inside, _json,
                           _keys, _now, strict_json, read_json)

CONFIG_SCHEMA = "bago.suite.collaboration.v1"
CONTEXT_SCHEMA = "bago.suite.relay.context.v1"
CHECKPOINT_SCHEMA = "bago.suite.relay.checkpoint.v1"
HANDOFF_SCHEMA = "bago.suite.relay.handoff.v1"


def validate_config(config, plan):
    _keys(config, {"schema", "workers", "verification_checks", "lease_seconds",
                   "max_claims", "max_handoffs", "max_checkpoints"})
    if config["schema"] != CONFIG_SCHEMA:
        raise ControlError("unsupported collaboration schema")
    bounds = {"lease_seconds": (5, 3600), "max_claims": (1, 10000),
              "max_handoffs": (1, 1000), "max_checkpoints": (1, 10000)}
    for key, (low, high) in bounds.items():
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ControlError(f"{key} must be an integer in [{low}, {high}]")
    workers = config["workers"]
    if not isinstance(workers, list) or not 2 <= len(workers) <= 100:
        raise ControlError("declare 2..100 logical workers")
    seen, roles = set(), set()
    for worker in workers:
        _keys(worker, {"id", "role"}); _id(worker["id"])
        if worker["id"] in seen or worker["role"] not in {"executor", "verifier"}:
            raise ControlError("duplicate worker or unsupported role")
        seen.add(worker["id"]); roles.add(worker["role"])
    if roles != {"executor", "verifier"}:
        raise ControlError("separate executor and verifier identities are required")
    verify = config["verification_checks"]
    checks = {c["id"]: c for c in plan["checks"]}
    if not isinstance(verify, list) or not verify or any(not isinstance(v, str) for v in verify):
        raise ControlError("verification_checks must be a nonempty list of check IDs")
    if len(verify) != len(set(verify)) or not set(verify) < set(checks):
        raise ControlError("verification checks must be a unique proper subset of plan checks")
    for key in verify:
        check = checks[key]
        if not check["mandatory"] or check["kind"] != "execution" or not check["depends_on"]:
            raise ControlError("verifier checks must be mandatory execution checks with dependencies")
    return config


def validate_context(value):
    _keys(value, {"schema", "summary", "completed", "pending", "decisions", "risks", "artifacts"})
    if value["schema"] != CONTEXT_SCHEMA:
        raise ControlError("unsupported relay context schema")
    if not isinstance(value["summary"], str) or not value["summary"].strip() or len(value["summary"]) > 8000:
        raise ControlError("context summary requires 1..8000 characters")
    for key in ("completed", "pending", "decisions", "risks"):
        values = value[key]
        if (not isinstance(values, list) or len(values) > 100 or
                any(not isinstance(x, str) or not x.strip() or len(x) > 2000 for x in values)):
            raise ControlError(f"invalid bounded context list: {key}")
    if not isinstance(value["artifacts"], list) or len(value["artifacts"]) > 100:
        raise ControlError("invalid context artifacts")
    if len(_json(value).encode("utf-8")) > 64000:
        raise ControlError("relay context exceeds 64 KB; refer to scoped evidence instead")
    seen = set()
    for artifact in value["artifacts"]:
        _keys(artifact, {"root", "path"})
        if artifact["root"] not in {"state", "workspace"}:
            raise ControlError("artifact root must be state or workspace")
        from suite_safety import safe_rel, collision_key
        safe_rel(artifact["path"])
        key = (artifact["root"], collision_key(artifact["path"]))
        if key in seen:
            raise ControlError("duplicate context artifact")
        seen.add(key)
        if artifact["root"] == "state" and not artifact["path"].startswith(("receipts/", "runs/")):
            raise ControlError("state artifacts are restricted to receipts/ and runs/; no live ledger copies")
    return value


class RelayController:
    """Extension of one TaskStore, using its transactions, candidate and receipts."""
    def __init__(self, store):
        self.store = store

    @staticmethod
    def enabled(meta):
        return "collaboration" in meta

    def config(self, meta):
        if not self.enabled(meta):
            raise ControlError("collaboration is not enabled for this mission")
        return validate_config(meta["collaboration"], meta["plan"])

    def enable(self, config):
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn, round_required=False)
            validate_config(config, meta["plan"])
            if (self.enabled(meta) or meta["round"] or
                    conn.execute("SELECT 1 FROM runs").fetchone() or
                    conn.execute("SELECT 1 FROM assignments").fetchone()):
                raise ControlError("enable collaboration once, immediately after task init and before rounds")
            # Deliberately no executescript: it can commit an existing transaction.
            statements = [
                """CREATE TABLE relay_work (check_id TEXT PRIMARY KEY, state TEXT NOT NULL,
                    worker TEXT, generation INTEGER NOT NULL DEFAULT 0, token_hash TEXT,
                    expires_at REAL, checkpoint_id TEXT)""",
                """CREATE TABLE relay_checkpoints (id TEXT PRIMARY KEY, check_id TEXT NOT NULL,
                    payload TEXT NOT NULL, sha256 TEXT NOT NULL)""",
                """CREATE TABLE relay_handoffs (id TEXT PRIMARY KEY, check_id TEXT NOT NULL,
                    state TEXT NOT NULL, payload TEXT NOT NULL, sha256 TEXT NOT NULL)""",
                """CREATE TABLE relay_claims (id TEXT PRIMARY KEY, check_id TEXT NOT NULL,
                    worker TEXT NOT NULL, generation INTEGER NOT NULL, at TEXT NOT NULL)""",
            ]
            for sql in statements:
                conn.execute(sql)
            conn.execute("INSERT INTO meta VALUES ('collaboration',?)", (_json(config),))
            conn.executemany("INSERT INTO relay_work(check_id,state) VALUES (?, 'AVAILABLE')",
                             [(c["id"],) for c in meta["plan"]["checks"]])
            self.store._event(conn, "COLLABORATION_ENABLED", {
                "config": config, "mode": "COOPERATIVE_SERIAL", "host_authentication": "NOT_PROVIDED"})
            conn.commit()
        return {"status": "PASS", "mode": "COOPERATIVE_SERIAL", "spawned": False,
                "authority": "HOST_ONLY", "config": config}

    def _worker(self, meta, check_id, worker):
        _id(worker)
        config = self.config(meta)
        self.store._check(meta, check_id)
        role = "verifier" if check_id in config["verification_checks"] else "executor"
        if not any(w == {"id": worker, "role": role} for w in config["workers"]):
            raise ControlError("worker is not registered for this check role")
        return role

    @staticmethod
    def _row(conn, check_id):
        row = conn.execute("SELECT * FROM relay_work WHERE check_id=?", (check_id,)).fetchone()
        if row is None:
            raise ControlError("check has no collaboration slot")
        return row

    def guard(self, conn, meta, check_id, worker, token, required_seconds=0):
        if not self.enabled(meta):
            return None
        self._worker(meta, check_id, worker)
        row = self._row(conn, check_id)
        if (row["state"] != "CLAIMED" or row["worker"] != worker or
                not isinstance(token, str) or len(token) != 64 or
                not row["token_hash"] or
                not hmac.compare_digest(row["token_hash"], _hash(token.encode()))):
            raise ControlError("missing, stale or foreign worker lease")
        if row["expires_at"] <= time.time() + required_seconds:
            raise ControlError("worker lease expired or too short for this check; renew explicitly")
        return row

    def _no_running(self, conn):
        if conn.execute("SELECT 1 FROM runs WHERE state='RUNNING'").fetchone():
            raise ControlError("a supervised check is still running or its exit is unconfirmed")

    def _no_other_owner(self, conn, check_id):
        if conn.execute("SELECT 1 FROM relay_work WHERE check_id<>? AND state IN ('CLAIMED','OFFERED','SUSPENDED')",
                        (check_id,)).fetchone():
            raise ControlError("serial collaboration: another check owns the mission")

    def _dependencies(self, conn, meta, check_id):
        check = self.store._check(meta, check_id)
        self.store._dependencies(conn, meta, check)
        for dep in check["depends_on"]:
            if self._row(conn, dep)["state"] != "DONE":
                raise ControlError("dependency has not completed its worker handoff lifecycle")

    def _grant(self, conn, meta, check_id, worker):
        config = self.config(meta)
        count = conn.execute("SELECT count(*) FROM relay_claims").fetchone()[0]
        if count >= config["max_claims"]:
            raise ControlError("frozen worker claim budget exhausted")
        row = self._row(conn, check_id)
        token = secrets.token_hex(32)
        generation = row["generation"] + 1
        expires = time.time() + config["lease_seconds"]
        conn.execute("UPDATE relay_work SET state='CLAIMED', worker=?, generation=?, token_hash=?, expires_at=? WHERE check_id=?",
                     (worker, generation, _hash(token.encode()), expires, check_id))
        conn.execute("INSERT INTO relay_claims VALUES (?,?,?,?,?)",
                     (uuid.uuid4().hex, check_id, worker, generation, _now()))
        self.store._event(conn, "RELAY_CLAIM", {"check_id": check_id, "worker": worker,
            "generation": generation, "expires_at": expires, "spawned": False})
        return {"status": "PASS", "check_id": check_id, "worker": worker, "generation": generation,
                "lease_token": token, "expires_at": expires, "spawned": False,
                "authority": "HOST_ONLY; lease is local coordination, not a permit"}

    def _observed_checks(self, conn, meta):
        values = []
        for row in conn.execute("SELECT * FROM checks ORDER BY id"):
            if row["receipt"]:
                self.store._validate_stored(conn, meta, row["id"])
            values.append(dict(row))
        return values

    def _checkpoint(self, conn, meta, check_id, worker, token, context):
        row = self.guard(conn, meta, check_id, worker, token)
        self._no_running(conn)
        validate_context(context)
        config = self.config(meta)
        if conn.execute("SELECT count(*) FROM relay_checkpoints").fetchone()[0] >= config["max_checkpoints"]:
            raise ControlError("frozen checkpoint budget exhausted")
        checkpoint_id = uuid.uuid4().hex
        artifacts = [self.store._artifact(meta, a["root"], a["path"], None) for a in context["artifacts"]]
        payload = {"schema": CHECKPOINT_SCHEMA, "checkpoint_id": checkpoint_id,
                   "mission_id": meta["plan"]["mission_id"], "candidate": meta["candidate"],
                   "workspace": meta["workspace"], "check_id": check_id, "worker": worker,
                   "generation": row["generation"], "round": meta["round"], "created_at": _now(),
                   "context": context, "artifacts": artifacts,
                   "observed_checks": self._observed_checks(conn, meta),
                   "context_claims_are_not_evidence": True}
        encoded = _json(payload); digest = _hash(encoded.encode())
        conn.execute("INSERT INTO relay_checkpoints VALUES (?,?,?,?)", (checkpoint_id, check_id, encoded, digest))
        conn.execute("UPDATE relay_work SET checkpoint_id=? WHERE check_id=?", (checkpoint_id, check_id))
        self.store._event(conn, "RELAY_CHECKPOINT", {"check_id": check_id, "checkpoint_id": checkpoint_id,
                                                    "sha256": digest, "worker": worker})
        return {"status": "PASS", "checkpoint_id": checkpoint_id, "sha256": digest, "packet": payload}

    def _validate_checkpoint(self, conn, meta, checkpoint_id, check_id):
        row = conn.execute("SELECT * FROM relay_checkpoints WHERE id=?", (checkpoint_id,)).fetchone()
        if not row or row["check_id"] != check_id or _hash(row["payload"].encode()) != row["sha256"]:
            raise ControlError("missing or altered relay checkpoint")
        p = strict_json(row["payload"])
        _keys(p, {"schema", "checkpoint_id", "mission_id", "candidate", "workspace", "check_id", "worker",
                  "generation", "round", "created_at", "context", "artifacts", "observed_checks", "context_claims_are_not_evidence"})
        if (p["schema"] != CHECKPOINT_SCHEMA or p["checkpoint_id"] != checkpoint_id or p["check_id"] != check_id or
                p["mission_id"] != meta["plan"]["mission_id"] or p["candidate"] != meta["candidate"] or
                p["workspace"] != meta["workspace"] or p["context_claims_are_not_evidence"] is not True):
            raise ControlError("checkpoint belongs to a different mission, candidate or schema")
        validate_context(p["context"])
        current = [self.store._artifact(meta, a["root"], a["path"], None) for a in p["context"]["artifacts"]]
        if current != p["artifacts"]:
            raise ControlError("handoff artifact changed; refuse stale continuation")
        if self._observed_checks(conn, meta) != p["observed_checks"]:
            raise ControlError("check evidence changed after checkpoint")
        return p, row["sha256"]

    def claim(self, check_id, worker):
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            self._worker(meta, check_id, worker); self._no_running(conn); self._no_other_owner(conn, check_id)
            row = self._row(conn, check_id)
            if row["state"] != "AVAILABLE":
                raise ControlError("work is not available; accept its handoff or recover it explicitly")
            self._dependencies(conn, meta, check_id)
            packet = self._validate_checkpoint(conn, meta, row["checkpoint_id"], check_id)[0] if row["checkpoint_id"] else None
            result = self._grant(conn, meta, check_id, worker)
            result["checkpoint"] = packet
            conn.commit()
        return result

    def heartbeat(self, check_id, worker, token):
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            self.guard(conn, meta, check_id, worker, token)
            expires = time.time() + self.config(meta)["lease_seconds"]
            conn.execute("UPDATE relay_work SET expires_at=? WHERE check_id=?", (expires, check_id))
            self.store._event(conn, "RELAY_HEARTBEAT", {"check_id": check_id, "worker": worker, "expires_at": expires})
            conn.commit()
        return {"status": "PASS", "expires_at": expires}

    def checkpoint(self, check_id, worker, token, context):
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            result = self._checkpoint(conn, meta, check_id, worker, token, context)
            conn.commit()
        return result

    def offer(self, check_id, worker, token, successor, context, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ControlError("handoff requires a bounded explicit reason")
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            self._worker(meta, check_id, successor)
            if worker == successor:
                raise ControlError("successor must be a different logical worker")
            config = self.config(meta)
            if conn.execute("SELECT count(*) FROM relay_handoffs").fetchone()[0] >= config["max_handoffs"]:
                raise ControlError("frozen handoff budget exhausted")
            validate_context(context)
            if not context["pending"]:
                raise ControlError("handoff must name remaining work")
            cp = self._checkpoint(conn, meta, check_id, worker, token, context)
            generation = self._row(conn, check_id)["generation"] + 1
            hid = uuid.uuid4().hex
            packet = {"schema": HANDOFF_SCHEMA, "handoff_id": hid, "check_id": check_id,
                      "mission_id": meta["plan"]["mission_id"], "candidate": meta["candidate"],
                      "from_worker": worker, "to_worker": successor, "generation": generation,
                      "checkpoint_id": cp["checkpoint_id"], "checkpoint_sha256": cp["sha256"],
                      "reason": reason, "created_at": _now()}
            encoded = _json(packet); digest = _hash(encoded.encode())
            conn.execute("INSERT INTO relay_handoffs VALUES (?,?,'OFFERED',?,?)", (hid, check_id, encoded, digest))
            conn.execute("UPDATE relay_work SET state='OFFERED', generation=?, token_hash=NULL, expires_at=NULL WHERE check_id=?",
                         (generation, check_id))
            self.store._event(conn, "RELAY_OFFER", {"handoff_id": hid, "sha256": digest,
                                                   "from_worker": worker, "to_worker": successor})
            conn.commit()
        return {"status": "PASS", "handoff_id": hid, "sha256": digest, "packet": packet,
                "checkpoint": cp["packet"], "old_lease_revoked": True, "spawned": False}

    def accept(self, handoff_id, worker, expected_sha256):
        _id(handoff_id)
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            self.config(meta); self._no_running(conn)
            row = conn.execute("SELECT * FROM relay_handoffs WHERE id=?", (handoff_id,)).fetchone()
            if not row or row["state"] != "OFFERED":
                raise ControlError("handoff is not pending; replayed acceptance is refused")
            digest = _hash(row["payload"].encode())
            if digest != row["sha256"] or expected_sha256 != digest:
                raise ControlError("handoff acknowledgment hash mismatch")
            p = strict_json(row["payload"])
            _keys(p, {"schema", "handoff_id", "check_id", "mission_id", "candidate", "from_worker", "to_worker",
                      "generation", "checkpoint_id", "checkpoint_sha256", "reason", "created_at"})
            if (p["schema"] != HANDOFF_SCHEMA or p["handoff_id"] != handoff_id or p["check_id"] != row["check_id"] or
                    p["to_worker"] != worker or p["mission_id"] != meta["plan"]["mission_id"] or p["candidate"] != meta["candidate"]):
                raise ControlError("handoff recipient, mission or candidate mismatch")
            check_id = p["check_id"]
            self._worker(meta, check_id, worker); self._no_other_owner(conn, check_id)
            slot = self._row(conn, check_id)
            if (slot["state"] != "OFFERED" or slot["generation"] != p["generation"] or
                    slot["checkpoint_id"] != p["checkpoint_id"] or slot["worker"] != p["from_worker"]):
                raise ControlError("handoff no longer owns the work generation")
            self._dependencies(conn, meta, check_id)
            packet, cp_hash = self._validate_checkpoint(conn, meta, p["checkpoint_id"], check_id)
            if cp_hash != p["checkpoint_sha256"]:
                raise ControlError("handoff checkpoint digest mismatch")
            result = self._grant(conn, meta, check_id, worker)
            conn.execute("UPDATE relay_handoffs SET state='ACCEPTED' WHERE id=?", (handoff_id,))
            self.store._event(conn, "RELAY_ACCEPT", {"handoff_id": handoff_id, "accepted_sha256": digest,
                                                    "worker": worker, "generation": result["generation"]})
            result.update({"handoff_id": handoff_id, "accepted_sha256": digest, "checkpoint": packet})
            conn.commit()
        return result

    def finish(self, check_id, worker, token):
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            self.guard(conn, meta, check_id, worker, token); self._no_running(conn)
            receipt, digest = self.store._validate_stored(conn, meta, check_id)
            evidence = conn.execute("SELECT * FROM checks WHERE id=?", (check_id,)).fetchone()
            if not evidence["consumed"] or receipt["outcome"] != "PASS":
                raise ControlError("worker finish requires consumed PASS evidence, not a narrative claim")
            conn.execute("UPDATE relay_work SET state='DONE', generation=generation+1, token_hash=NULL, expires_at=NULL WHERE check_id=?", (check_id,))
            self.store._event(conn, "RELAY_FINISH", {"check_id": check_id, "worker": worker, "receipt_sha256": digest})
            conn.commit()
        return {"status": "PASS", "check_id": check_id, "worker": worker, "work_state": "DONE",
                "product_status": "LIMITED_TO_CHECK; mission closure is separate"}

    def release(self, check_id, worker, token, context, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ControlError("release requires an explicit reason")
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            cp = self._checkpoint(conn, meta, check_id, worker, token, context)
            conn.execute("UPDATE relay_work SET state='AVAILABLE', worker=NULL, generation=generation+1, token_hash=NULL, expires_at=NULL WHERE check_id=?", (check_id,))
            self.store._event(conn, "RELAY_RELEASE", {"check_id": check_id, "worker": worker, "reason": reason,
                                                      "checkpoint_id": cp["checkpoint_id"]})
            conn.commit()
        return {"status": "PASS", "work_state": "AVAILABLE", "checkpoint_id": cp["checkpoint_id"]}

    def recover(self, check_id, reason, confirm_prior_stopped=False):
        if not confirm_prior_stopped or not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
            raise ControlError("recovery requires reason and host confirmation that the prior worker stopped")
        with self.store.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self.store._admit(conn)
            self.config(meta); self.store._check(meta, check_id); self._no_running(conn)
            row = self._row(conn, check_id)
            expired = row["state"] == "CLAIMED" and row["expires_at"] <= time.time()
            if not expired and row["state"] != "SUSPENDED":
                raise ControlError("only expired or STOP-suspended ownership may be recovered")
            conn.execute("UPDATE relay_handoffs SET state='CANCELLED' WHERE check_id=? AND state='OFFERED'", (check_id,))
            conn.execute("UPDATE relay_work SET state='AVAILABLE', worker=NULL, generation=generation+1, token_hash=NULL, expires_at=NULL WHERE check_id=?", (check_id,))
            self.store._event(conn, "RELAY_RECOVER", {"check_id": check_id, "prior_worker": row["worker"],
                "reason": reason, "host_confirmation": "DECLARED_BY_CALLER", "external_effects": "NOT_VERIFIED"})
            conn.commit()
        return {"status": "PASS", "work_state": "AVAILABLE", "external_effects": "NOT_VERIFIED",
                "warning": "Reconcile external effects before retry; recovery does not prove exactly-once execution."}

    def on_stop(self, conn, meta):
        if not self.enabled(meta):
            return
        conn.execute("UPDATE relay_work SET state='SUSPENDED', generation=generation+1, token_hash=NULL, expires_at=NULL WHERE state IN ('CLAIMED','OFFERED')")
        self.store._event(conn, "RELAY_LEASES_REVOKED", {"reason": "STOP", "external_interrupt": "NOT_RUN"})

    def idle(self, conn, meta):
        if self.enabled(meta) and conn.execute("SELECT 1 FROM relay_work WHERE state IN ('CLAIMED','OFFERED','SUSPENDED')").fetchone():
            raise ControlError("finish, release or recover collaboration ownership before a new round")

    def incomplete(self, conn, meta):
        return self.enabled(meta) and bool(conn.execute("SELECT 1 FROM relay_work WHERE state<>'DONE'").fetchone())

    def summary(self, conn, meta):
        if not self.enabled(meta):
            return {"enabled": False}
        return {"enabled": True, "mode": "COOPERATIVE_SERIAL", "host_authentication": "NOT_PROVIDED",
                "workers": meta["collaboration"]["workers"],
                "work": [dict(r) for r in conn.execute("SELECT check_id,state,worker,generation,expires_at,checkpoint_id FROM relay_work ORDER BY check_id")],
                "handoffs": [dict(r) for r in conn.execute("SELECT id,check_id,state,sha256 FROM relay_handoffs ORDER BY rowid")],
                "claims_used": conn.execute("SELECT count(*) FROM relay_claims").fetchone()[0],
                "checkpoints_used": conn.execute("SELECT count(*) FROM relay_checkpoints").fetchone()[0]}

    def guide(self):
        with self.store.db() as conn:
            conn.execute("BEGIN")
            meta = self.store._meta(conn); self.config(meta); self.store._candidate(meta)
            result = {"status": "PASS", "mission_id": meta["plan"]["mission_id"], "round": meta["round"],
                      "spawned": False, "reasoning": "HOST_REQUIRED", "collaboration": self.summary(conn, meta)}
            if meta["closed"]:
                action = {"action": "CLOSED"}
            elif meta["control"] != "ACTIVE":
                action = {"action": "EXPLICIT_RESUME_REQUIRED"}
            elif conn.execute("SELECT 1 FROM runs WHERE state='RUNNING'").fetchone():
                action = {"action": "WAIT_OR_CONFIRM_SUPERVISED_PROCESS_EXIT"}
            else:
                row = conn.execute("SELECT * FROM relay_work WHERE state IN ('CLAIMED','OFFERED','SUSPENDED') ORDER BY check_id LIMIT 1").fetchone()
                if row and row["state"] == "OFFERED":
                    offered = conn.execute("SELECT * FROM relay_handoffs WHERE check_id=? AND state='OFFERED'", (row["check_id"],)).fetchone()
                    if not offered:
                        raise ControlError("offered work has no handoff")
                    p = strict_json(offered["payload"])
                    action = {"action": "ACCEPT_HANDOFF", "handoff_id": offered["id"], "worker": p["to_worker"], "sha256": offered["sha256"]}
                elif row:
                    recovery = row["state"] == "SUSPENDED" or row["expires_at"] <= time.time()
                    action = {"action": "RECOVER_WITH_HOST_CONFIRMATION" if recovery else "CONTINUE_OR_CHECKPOINT",
                              "check_id": row["check_id"], "worker": row["worker"]}
                elif not meta["round"]:
                    action = {"action": "OPEN_ROUND"}
                elif not self.incomplete(conn, meta):
                    action = {"action": "CLOSE_WITH_EXISTING_EVIDENCE_GATE"}
                else:
                    ready, blocked = [], []
                    needs_round = False
                    for slot in conn.execute("SELECT * FROM relay_work WHERE state='AVAILABLE' ORDER BY check_id"):
                        try:
                            self._dependencies(conn, meta, slot["check_id"])
                        except ControlError as exc:
                            blocked.append({"check_id": slot["check_id"], "reason": str(exc)}); continue
                        if conn.execute("SELECT 1 FROM runs WHERE check_id=? AND round=?", (slot["check_id"], meta["round"])).fetchone():
                            needs_round = True; continue
                        role = "verifier" if slot["check_id"] in meta["collaboration"]["verification_checks"] else "executor"
                        ready.append({"check_id": slot["check_id"], "role": role,
                                      "workers": [w["id"] for w in meta["collaboration"]["workers"] if w["role"] == role]})
                    action = {"action": "CLAIM" if ready else ("OPEN_ROUND" if needs_round and meta["round"] < meta["plan"]["max_rounds"] else "BLOCKED"),
                              "eligible": ready, "blocked": blocked}
            result["next"] = action
            return result


def add_parser(actions):
    parser = actions.add_parser("collaborate", help="Cooperative serial relays inside this task ledger; no agent daemon")
    actions = parser.add_subparsers(dest="relay_action", required=True)
    demo = actions.add_parser("demo", help="Three deterministic fixture processes; not LLM agents")
    demo.add_argument("--output", required=True, type=Path)
    for name in ("enable", "guide", "claim", "heartbeat", "checkpoint", "offer", "accept", "release", "finish", "recover"):
        p = actions.add_parser(name)
        p.add_argument("--state-dir", required=True, type=Path)
        if name == "enable": p.add_argument("--config", type=Path, required=True)
        if name not in {"enable", "guide", "accept"}: p.add_argument("--check", required=True)
        if name not in {"enable", "guide", "recover"}: p.add_argument("--worker", required=True)
        if name in {"checkpoint", "offer", "release"}: p.add_argument("--context", required=True, type=Path)
        if name in {"offer", "release", "recover"}: p.add_argument("--reason", required=True)
        if name == "offer": p.add_argument("--to-worker", required=True)
        if name == "accept":
            p.add_argument("--handoff", required=True); p.add_argument("--ack-sha256", required=True)
        if name == "recover": p.add_argument("--confirm-prior-stopped", action="store_true")
    return parser


def execute(args, store):
    relay = RelayController(store)
    a = args.relay_action
    token = os.environ.get("BAGO_RELAY_TOKEN")
    if a == "enable": return relay.enable(read_json(args.config, max_bytes=64000))
    if a == "guide": return relay.guide()
    if a == "claim": return relay.claim(args.check, args.worker)
    if a == "accept": return relay.accept(args.handoff, args.worker, args.ack_sha256)
    if a == "recover": return relay.recover(args.check, args.reason, args.confirm_prior_stopped)
    if a == "heartbeat": return relay.heartbeat(args.check, args.worker, token)
    if a == "finish": return relay.finish(args.check, args.worker, token)
    context = read_json(args.context, max_bytes=64000)
    if a == "checkpoint": return relay.checkpoint(args.check, args.worker, token, context)
    if a == "offer": return relay.offer(args.check, args.worker, token, args.to_worker, context, args.reason)
    if a == "release": return relay.release(args.check, args.worker, token, context, args.reason)
    raise ControlError("unsupported collaboration action")
