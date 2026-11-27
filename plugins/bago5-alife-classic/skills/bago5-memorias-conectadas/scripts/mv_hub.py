#!/usr/bin/env python3
"""BAGO5 Memory Federation: optional standalone loopback reference hub.

Not a ChatGPT Site, not an OAuth/MCP implementation. No external URL is contacted.
Memory access is authorized by bearer credentials at the HTTP boundary. The
local administrator who controls the SQLite file can provision accounts.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sqlite3
import sys
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

MAX_PACK_BYTES = 32 * 1024 * 1024
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MEMBERS = ("manifest.json", "projects.json", "memories.json", "revisions.json", "SHA256SUMS.txt", "LEEME.md")
ALIAS = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{1,63}$")


class HubError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(blob: bytes | str) -> str:
    if isinstance(blob, str):
        blob = blob.encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def uid():
    return str(uuid.uuid4())


def json_bytes(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def must(cond, code):
    if not cond:
        raise HubError(code)


def fields(row):
    return dict(row) if row is not None else None


class Hub:
    def __init__(self, file: str | Path):
        self.file = Path(file).expanduser().resolve()
        self.file.parent.mkdir(parents=True, exist_ok=True)
        existed = self.file.exists()
        self.db = sqlite3.connect(str(self.file), timeout=10, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=10000")
        if not existed and os.name == "posix":
            self.file.chmod(0o600)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS stores(id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES accounts(id), name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id), name TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id),
            project_id TEXT NOT NULL REFERENCES projects(id), title TEXT NOT NULL, content TEXT NOT NULL,
            kind TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL, origin_key TEXT,
            source TEXT NOT NULL DEFAULT '', tags_json TEXT NOT NULL DEFAULT '[]', pinned INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0, decision_closed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(store_id,origin_key));
        CREATE TABLE IF NOT EXISTS revisions(memory_id TEXT NOT NULL REFERENCES memories(id), version INTEGER NOT NULL,
            snapshot TEXT NOT NULL, timestamp TEXT NOT NULL, PRIMARY KEY(memory_id,version));
        CREATE TABLE IF NOT EXISTS invitations(id TEXT PRIMARY KEY, store_id TEXT NOT NULL REFERENCES stores(id),
            project_id TEXT REFERENCES projects(id), role TEXT NOT NULL, recipient_id TEXT NOT NULL REFERENCES accounts(id),
            secret_hash TEXT NOT NULL, expires_at TEXT NOT NULL, issued_by TEXT NOT NULL REFERENCES accounts(id),
            accepted_at TEXT, revoked_at TEXT);
        CREATE TABLE IF NOT EXISTS grants(id TEXT PRIMARY KEY, invitation_id TEXT NOT NULL UNIQUE REFERENCES invitations(id),
            store_id TEXT NOT NULL REFERENCES stores(id), project_id TEXT REFERENCES projects(id),
            user_id TEXT NOT NULL REFERENCES accounts(id), role TEXT NOT NULL, revoked_at TEXT);
        CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES accounts(id),
            alias TEXT NOT NULL, endpoint TEXT NOT NULL, expected_identity TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'UNVERIFIED', selected INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id,alias));
        CREATE TABLE IF NOT EXISTS import_map(dest_store_id TEXT NOT NULL REFERENCES stores(id),
            src_store_id TEXT NOT NULL, src_project_id TEXT NOT NULL,
            dest_project_id TEXT NOT NULL REFERENCES projects(id),
            PRIMARY KEY(dest_store_id,src_store_id,src_project_id));
        """)

    def close(self):
        self.db.close()

    def _row(self, query, args=()):
        return self.db.execute(query, args).fetchone()

    def add_account(self, name):
        must(isinstance(name, str) and ALIAS.fullmatch(name), "BAD_ACCOUNT_ID")
        token = secrets.token_urlsafe(40)
        try:
            self.db.execute("INSERT INTO accounts VALUES(?,?)", (name, digest(token)))
        except sqlite3.IntegrityError as exc:
            raise HubError("ACCOUNT_EXISTS") from exc
        return token  # reveal exactly once; never store plaintext or write in packs

    def actor(self, token):
        must(isinstance(token, str) and len(token) >= 40, "AUTH_REQUIRED")
        row = self._row("SELECT id FROM accounts WHERE token_hash=?", (digest(token),))
        must(row is not None, "AUTH_DENIED")
        return row["id"]

    def store_add(self, token, name):
        owner = self.actor(token)
        must(isinstance(name, str) and 0 < len(name) <= 180, "BAD_STORE_NAME")
        sid = uid()
        self.db.execute("INSERT INTO stores VALUES(?,?,?)", (sid, owner, name))
        return sid

    def _role(self, actor, sid, pid=None):
        row = self._row("SELECT owner_id FROM stores WHERE id=?", (sid,))
        must(row is not None, "STORE_NOT_FOUND")
        if row["owner_id"] == actor:
            return "owner"
        grants = self.db.execute("SELECT role,project_id FROM grants WHERE store_id=? AND user_id=? AND revoked_at IS NULL", (sid, actor)).fetchall()
        scoped = [x["role"] for x in grants if x["project_id"] is None or x["project_id"] == pid]
        return "editor" if "editor" in scoped else ("viewer" if "viewer" in scoped else None)

    def _allow(self, actor, sid, pid, write=False, owner=False):
        role = self._role(actor, sid, pid)
        must(role == "owner" if owner else role in (("owner", "editor") if write else ("owner", "editor", "viewer")), "ACCESS_DENIED")

    def stores(self, token):
        actor = self.actor(token)
        rows = self.db.execute("SELECT id, name, owner_id FROM stores").fetchall()
        return [fields(r) for r in rows if self._role(actor, r["id"]) is not None]

    def project_add(self, token, sid, name):
        a = self.actor(token)
        self._allow(a, sid, None, owner=True)
        must(isinstance(name, str) and 0 < len(name) <= 180, "BAD_PROJECT_NAME")
        pid = uid()
        self.db.execute("INSERT INTO projects VALUES(?,?,?)", (pid, sid, name))
        return pid

    def projects(self, token, sid):
        a = self.actor(token)
        self._allow(a, sid, None) if self._role(a, sid, None) else None
        result = self.db.execute("SELECT id,name,store_id FROM projects WHERE store_id=?", (sid,)).fetchall()
        return [fields(r) for r in result if self._role(a, sid, r["id"]) is not None]

    def memory_put(self, token, sid, pid, title, content, kind=None, status=None, memory_id=None, expected_version=None, *, source=None, tags=None, pinned=None, archived=None, decision_closed=None):
        a = self.actor(token)
        must(self._row("SELECT 1 FROM projects WHERE id=? AND store_id=?", (pid, sid)) is not None, "PROJECT_NOT_FOUND")
        self._allow(a, sid, pid, write=True)
        must(isinstance(title, str) and 0 < len(title) <= 180 and isinstance(content, str) and 0 < len(content) <= 30000, "BAD_MEMORY")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self._row("SELECT * FROM memories WHERE id=? AND store_id=?", (memory_id, sid)) if memory_id else None
            if memory_id and existing is None:
                raise HubError("MEMORY_NOT_FOUND")
            if existing:
                kind=existing["kind"] if kind is None else kind
                status=existing["status"] if status is None else status
                source=existing["source"] if source is None else source
                tags=json.loads(existing["tags_json"]) if tags is None else tags
                pinned=bool(existing["pinned"]) if pinned is None else pinned
                archived=bool(existing["archived"]) if archived is None else archived
                decision_closed=bool(existing["decision_closed"]) if decision_closed is None else decision_closed
            else:
                kind="context" if kind is None else kind
                status="active" if status is None else status
                source="" if source is None else source
                tags=[] if tags is None else tags
                pinned=False if pinned is None else pinned
                archived=False if archived is None else archived
                decision_closed=False if decision_closed is None else decision_closed
            must(kind in ("context", "idea", "learning", "decision") and status in ("active", "pending", "superseded"), "BAD_MEMORY_TYPE")
            must(isinstance(source,str) and len(source)<=1000 and isinstance(tags,list) and len(tags)<=12 and all(isinstance(t,str) and 0<len(t)<=40 for t in tags) and all(type(v)==bool for v in (pinned,archived,decision_closed)),"BAD_MEMORY_METADATA")
            if existing:
                must(existing["project_id"] == pid, "PROJECT_MISMATCH")
                must(expected_version == existing["version"], "VERSION_CONFLICT")
                version = existing["version"] + 1
                self.db.execute("UPDATE memories SET title=?,content=?,kind=?,status=?,version=?,source=?,tags_json=?,pinned=?,archived=?,decision_closed=? WHERE id=?", (title,content,kind,status,version,source,json_bytes(tags).decode(),int(pinned),int(archived),int(decision_closed),memory_id))
            else:
                must(expected_version is None, "UNEXPECTED_VERSION")
                memory_id, version = uid(), 1
                self.db.execute("INSERT INTO memories(id,store_id,project_id,title,content,kind,status,version,source,tags_json,pinned,archived,decision_closed) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (memory_id,sid,pid,title,content,kind,status,version,source,json_bytes(tags).decode(),int(pinned),int(archived),int(decision_closed)))
            snap={"title":title,"content":content,"kind":kind,"status":status,"version":version,"source":source,"tags":tags,"pinned":pinned,"archived":archived,"decision_closed":decision_closed}
            self.db.execute("INSERT INTO revisions VALUES(?,?,?,?)", (memory_id,version,json_bytes(snap).decode(),now()))
            self.db.execute("COMMIT")
            return {"id":memory_id,"version":version}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def memories(self, token, sid, pid=None):
        actor = self.actor(token)
        rows = self.db.execute("SELECT * FROM memories WHERE store_id=?"+(" AND project_id=?" if pid else "")+" ORDER BY id", (sid,pid) if pid else (sid,)).fetchall()
        out=[]
        for r in rows:
            if self._role(actor,sid,r["project_id"]) is None: continue
            obj=fields(r);obj["tags"]=json.loads(obj.pop("tags_json"))
            for key in ("pinned","archived","decision_closed"):obj[key]=bool(obj[key])
            out.append(obj)
        return out

    def invite_issue(self, token, sid, recipient, role, project_id=None, hours=24):
        actor=self.actor(token)
        self._allow(actor,sid,None,owner=True)
        must(role in ("viewer","editor") and isinstance(hours,int) and 1<=hours<=720, "BAD_INVITATION")
        must(self._row("SELECT 1 FROM accounts WHERE id=?", (recipient,)) is not None, "RECIPIENT_UNKNOWN")
        if project_id:
            must(self._row("SELECT 1 FROM projects WHERE id=? AND store_id=?",(project_id,sid)) is not None,"PROJECT_NOT_FOUND")
        secret=secrets.token_urlsafe(32)
        inv_id=uid()
        expiry=(datetime.now(timezone.utc)+timedelta(hours=hours)).isoformat()
        self.db.execute("INSERT INTO invitations(id,store_id,project_id,role,recipient_id,secret_hash,expires_at,issued_by) VALUES(?,?,?,?,?,?,?,?)",
                        (inv_id,sid,project_id,role,recipient,digest(secret),expiry,actor))
        return {"invitation_id":inv_id,"token":secret,"recipient_id":recipient,"expires_at":expiry,"scope":project_id,"role":role}

    def invite_accept(self, token, invitation_id, invitation_secret):
        actor=self.actor(token)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            inv=self._row("SELECT * FROM invitations WHERE id=?",(invitation_id,))
            must(inv is not None,"INVITATION_NOT_FOUND")
            must(inv["recipient_id"]==actor,"WRONG_RECIPIENT")
            must(inv["revoked_at"] is None and inv["accepted_at"] is None,"INVITATION_INACTIVE")
            must(datetime.fromisoformat(inv["expires_at"])>datetime.now(timezone.utc),"INVITATION_EXPIRED")
            must(isinstance(invitation_secret,str) and hmac.compare_digest(digest(invitation_secret),inv["secret_hash"]),"INVITATION_SECRET_INVALID")
            self.db.execute("UPDATE invitations SET accepted_at=? WHERE id=?",(now(),invitation_id))
            gid=uid()
            self.db.execute("INSERT INTO grants(id,invitation_id,store_id,project_id,user_id,role) VALUES(?,?,?,?,?,?)",
                            (gid,invitation_id,inv["store_id"],inv["project_id"],actor,inv["role"]))
            self.db.execute("COMMIT")
            return {"grant_id":gid,"role":inv["role"],"store_id":inv["store_id"],"project_id":inv["project_id"]}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def invite_revoke(self, token, invitation_id):
        actor=self.actor(token)
        inv=self._row("SELECT * FROM invitations WHERE id=?",(invitation_id,))
        must(inv is not None,"INVITATION_NOT_FOUND")
        self._allow(actor,inv["store_id"],None,owner=True)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            stamp=now()
            self.db.execute("UPDATE invitations SET revoked_at=? WHERE id=?",(stamp,invitation_id))
            self.db.execute("UPDATE grants SET revoked_at=? WHERE invitation_id=? AND revoked_at IS NULL",(stamp,invitation_id))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return {"revoked": True, "grant_revoked": True}

    def invitations(self, token, sid):
        actor=self.actor(token)
        self._allow(actor,sid,None,owner=True)
        rows=self.db.execute("SELECT id,store_id,project_id,role,recipient_id,expires_at,accepted_at,revoked_at FROM invitations WHERE store_id=?",(sid,)).fetchall()
        return [fields(r) for r in rows] # never reveal invitation tokens or secret digests

    def connection_add(self, token, alias, endpoint, expected_identity):
        actor=self.actor(token)
        must(isinstance(alias,str) and ALIAS.fullmatch(alias),"BAD_ALIAS")
        must(isinstance(endpoint,str) and isinstance(expected_identity,str) and 0<len(expected_identity)<=200,"BAD_CONNECTION")
        u=urlsplit(endpoint)
        must(u.scheme=="https" and bool(u.hostname) and not u.username and not u.password and u.query=="" and u.fragment=="" and u.path.endswith("/mcp"),"UNSAFE_MCP_URL")
        try:
            cid=uid()
            self.db.execute("INSERT INTO connections(id,user_id,alias,endpoint,expected_identity) VALUES(?,?,?,?,?)",(cid,actor,alias,endpoint,expected_identity))
        except sqlite3.IntegrityError as exc:
            raise HubError("ALIAS_ALREADY_EXISTS") from exc
        return {"id":cid,"alias":alias,"state":"UNVERIFIED"}

    def connections(self, token):
        actor=self.actor(token)
        return [fields(x) for x in self.db.execute("SELECT id,alias,endpoint,expected_identity,state,selected FROM connections WHERE user_id=? ORDER BY alias",(actor,)).fetchall()]

    def connection_select(self, token, alias):
        actor=self.actor(token)
        must(self._row("SELECT 1 FROM connections WHERE user_id=? AND alias=?",(actor,alias)) is not None,"ALIAS_NOT_FOUND")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("UPDATE connections SET selected=0 WHERE user_id=?",(actor,))
            self.db.execute("UPDATE connections SET selected=1 WHERE user_id=? AND alias=?",(actor,alias))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return {"alias":alias,"state":"UNVERIFIED", "note":"Selection does not prove connection or ownership"}

    def connection_remove(self, token, alias):
        actor=self.actor(token)
        n=self.db.execute("DELETE FROM connections WHERE user_id=? AND alias=?",(actor,alias)).rowcount
        must(n>0,"ALIAS_NOT_FOUND")
        return {"removed":alias}

    def pack_export(self, token, sid, path, project_id=None):
        actor=self.actor(token)
        self._allow(actor,sid,project_id) if project_id else self._allow(actor,sid,None,owner=True)
        projects=self.projects(token,sid)
        if project_id:
            projects=[p for p in projects if p["id"]==project_id]
        pids={p["id"] for p in projects}
        records=[m for m in self.memories(token,sid) if m["project_id"] in pids]
        revisions=[]
        for m in records:
            for r in self.db.execute("SELECT version,snapshot,timestamp FROM revisions WHERE memory_id=? ORDER BY version",(m["id"],)).fetchall():
                revisions.append(dict(memory_id=m["id"],version=r["version"],snapshot=json.loads(r["snapshot"]),timestamp=r["timestamp"]))
        manifest=dict(schema="memoria-viva-pack.v1",source_store_id=sid,exported_at=now(),counts={"projects":len(projects),"memories":len(records),"revisions":len(revisions)},scope=project_id or "owner_full_store",credential_free=True)
        payload={"manifest.json":json_bytes(manifest),"projects.json":json_bytes(projects),"memories.json":json_bytes(records),"revisions.json":json_bytes(revisions),"LEEME.md":b"# Memoria Viva Pack v1\nSnapshot portable sin credenciales ni permisos transferibles. SHA256 no es firma de autor.\n"}
        hashes="".join(f"{digest(data)}  {name}\n" for name,data in sorted(payload.items()))
        payload["SHA256SUMS.txt"]=hashes.encode("ascii")
        must(sum(len(v) for v in payload.values())<=MAX_PACK_BYTES,"PACK_EXPORT_LIMIT")
        dest=Path(path)
        must(not dest.exists(),"DESTINATION_EXISTS")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(dest,"x",compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in payload.items():
                z.writestr(name,data)
        return {"path":str(dest),"counts":manifest["counts"],"sha256":digest(dest.read_bytes())}

    @staticmethod
    def _read_pack(path):
        p=Path(path)
        must(p.is_file() and p.stat().st_size<=MAX_PACK_BYTES,"PACK_SIZE_OR_MISSING")
        try:
            with zipfile.ZipFile(p) as z:
                entries=z.infolist()
                names=[i.filename for i in entries]
                must(set(names)==set(MEMBERS) and len(names)==len(MEMBERS),"PACK_MEMBER_INVALID")
                must(all(i.file_size<=MAX_MEMBER_BYTES for i in entries) and sum(i.file_size for i in entries)<=MAX_PACK_BYTES,"PACK_DECOMPRESSION_LIMIT")
                raw={n:z.read(n) for n in names}
        except (zipfile.BadZipFile,RuntimeError,OSError,ValueError) as exc:
            raise HubError("BAD_ZIP") from exc
        expected={}
        for line in raw["SHA256SUMS.txt"].decode("ascii").splitlines():
            sha,sep,name=line.partition("  ")
            must(sep and name not in expected and len(sha)==64,"BAD_HASH_LIST")
            expected[name]=sha
        must(set(expected)==set(MEMBERS)-{"SHA256SUMS.txt"},"BAD_HASH_LIST")
        must(all(hmac.compare_digest(digest(raw[n]),expected[n]) for n in expected),"HASH_MISMATCH")
        try:
            objs={n:json.loads(raw[n]) for n in ("manifest.json","projects.json","memories.json","revisions.json")}
        except (ValueError,UnicodeError) as exc:
            raise HubError("PACK_JSON_INVALID") from exc
        man=objs["manifest.json"]
        must(isinstance(man,dict) and man.get("schema")=="memoria-viva-pack.v1" and isinstance(man.get("source_store_id"),str) and len(man["source_store_id"])>0,"UNSUPPORTED_PACK")
        pjs,mems,revs=objs["projects.json"],objs["memories.json"],objs["revisions.json"]
        must(all(isinstance(v,list) for v in (pjs,mems,revs)) and len(pjs)<=1000 and len(mems)<=10000 and len(revs)<=50000,"PACK_DATA_INVALID")
        must(man.get("counts")==dict(projects=len(pjs),memories=len(mems),revisions=len(revs)),"COUNT_MISMATCH")
        ids=set()
        for p0 in pjs:
            must(isinstance(p0,dict) and isinstance(p0.get("id"),str) and isinstance(p0.get("name"),str) and 0<len(p0["name"])<=180 and p0["id"] not in ids and p0.get("store_id")==man["source_store_id"],"BAD_PROJECT")
            ids.add(p0["id"])
        mids=set();mvers={}
        for m in mems:
            must(isinstance(m,dict) and (m.get("origin_key") is None or (isinstance(m.get("origin_key"),str) and "::" in m["origin_key"] and len(m["origin_key"])<=300)) and isinstance(m.get("id"),str) and m["id"] not in mids and m.get("store_id")==man["source_store_id"] and m.get("project_id") in ids and isinstance(m.get("title"),str) and 0<len(m["title"])<=180 and isinstance(m.get("content"),str) and 0<len(m["content"])<=30000 and isinstance(m.get("version"),int) and m["version"]>=1 and m.get("kind") in ("context","idea","learning","decision") and m.get("status") in ("active","pending","superseded") and isinstance(m.get("source"),str) and len(m["source"])<=1000 and isinstance(m.get("tags"),list) and len(m["tags"])<=12 and all(isinstance(t,str) and 0<len(t)<=40 for t in m["tags"]) and all(type(m.get(k))==bool for k in ("pinned","archived","decision_closed")),"BAD_MEMORY")
            mids.add(m["id"]);mvers[m["id"]]=m["version"]
        rv={}
        for r in revs:
            must(isinstance(r,dict) and r.get("memory_id") in mids and isinstance(r.get("version"),int) and r["version"]>=1 and isinstance(r.get("snapshot"),dict) and isinstance(r.get("timestamp"),str),"BAD_REVISION")
            rv.setdefault(r["memory_id"],set())
            must(r["version"] not in rv[r["memory_id"]],"DUPLICATE_REVISION")
            rv[r["memory_id"]].add(r["version"])
        must(all(rv.get(k)==set(range(1,n+1)) for k,n in mvers.items()),"REVISION_GAP")
        # Verify the latest historical snapshot describes the exported current state.
        latest={(r["memory_id"],r["version"]):r["snapshot"] for r in revs}
        for m in mems:
            snap=latest[(m["id"],m["version"])]
            must(all(snap.get(k)==m.get(k) for k in ("title","content","kind","status","version","source","tags","pinned","archived","decision_closed")),"SNAPSHOT_MISMATCH")
        return objs

    def pack_import(self, token, sid, path, commit=False):
        actor=self.actor(token)
        self._allow(actor,sid,None,owner=True)
        objs=self._read_pack(path)
        src=objs["manifest.json"]["source_store_id"]
        must(src!=sid,"SELF_IMPORT_NOT_ALLOWED")
        projects=objs["projects.json"];memories=objs["memories.json"];revisions=objs["revisions.json"]
        self.db.execute("BEGIN IMMEDIATE")
        try:
            pmap={};new_projects=0
            for p in projects:
                old=self._row("SELECT dest_project_id FROM import_map WHERE dest_store_id=? AND src_store_id=? AND src_project_id=?",(sid,src,p["id"]))
                if old:
                    pmap[p["id"]]=old["dest_project_id"]
                else:
                    new_id=uid();pmap[p["id"]]=new_id;new_projects+=1
                    self.db.execute("INSERT INTO projects VALUES(?,?,?)",(new_id,sid,p["name"]))
                    self.db.execute("INSERT INTO import_map VALUES(?,?,?,?)",(sid,src,p["id"],new_id))
            new=0;skipped=0;mapping={}
            for m in memories:
                origin=m.get("origin_key") or (src+"::"+m["id"])
                old=self._row("SELECT id,title,content,version,kind,status,source,tags_json,pinned,archived,decision_closed FROM memories WHERE store_id=? AND origin_key=?",(sid,origin))
                if old:
                    must(all((bool(old[k]) if k in ("pinned","archived","decision_closed") else (json.loads(old["tags_json"]) if k=="tags" else old[k]))==m[k] for k in ("title","content","version","kind","status","source","tags","pinned","archived","decision_closed")),"IMPORT_CONFLICT")
                    skipped+=1;mapping[m["id"]]=old["id"]
                else:
                    new+=1;mid=uid();mapping[m["id"]]=mid
                    self.db.execute("INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(mid,sid,pmap[m["project_id"]],m["title"],m["content"],m["kind"],m["status"],m["version"],origin,m["source"],json_bytes(m["tags"]).decode(),int(m["pinned"]),int(m["archived"]),int(m["decision_closed"])))
            if new:
                # Skip already-existing revisions by PK; new rows have none.
                for r in revisions:
                    mid=mapping[r["memory_id"]]
                    if self._row("SELECT 1 FROM revisions WHERE memory_id=? AND version=?",(mid,r["version"])):
                        continue
                    self.db.execute("INSERT INTO revisions VALUES(?,?,?,?)",(mid,r["version"],json_bytes(r["snapshot"]).decode(),r["timestamp"]))
            report={"projects_created":new_projects,"memories_created":new,"memories_skipped":skipped,"committed":bool(commit)}
            self.db.execute("COMMIT" if commit else "ROLLBACK")
            return report
        except Exception:
            self.db.execute("ROLLBACK")
            raise


def make_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # no auth header, tokens or URLs in access logs

        def result(self, code, data):
            out=json_bytes(data)
            self.send_response(code)
            self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Content-Length",str(len(out)))
            self.end_headers()
            self.wfile.write(out)

        def run_request(self, post=False):
            if self.path=="/health" and not post:
                return self.result(200,{"service":"mv-hub-local","status":"ok","site_mcp":False})
            token=self.headers.get("Authorization","")
            must(token.startswith("Bearer "),"AUTH_REQUIRED")
            token=token[7:]
            body={}
            if post:
                size=int(self.headers.get("Content-Length","0"))
                must(0<size<=65536,"REQUEST_SIZE")
                try: body=json.loads(self.rfile.read(size))
                except (ValueError,UnicodeError) as exc: raise HubError("BAD_JSON") from exc
                must(isinstance(body,dict),"BAD_JSON")
            path,_,query=self.path.partition("?")
            qs=parse_qs(query)
            with_hub=Hub(db_path)
            try:
                h=with_hub;h.actor(token)
                if not post and path=="/stores": return self.result(200,{"stores":h.stores(token)})
                if not post and path=="/connections": return self.result(200,{"connections":h.connections(token)})
                if not post and path=="/memories":
                    return self.result(200,{"memories":h.memories(token,qs.get("store",[""])[0],qs.get("project",[None])[0])})
                if not post and path=="/projects": return self.result(200,{"projects":h.projects(token,qs.get("store",[""])[0])})
                if not post and path=="/invitations": return self.result(200,{"invitations":h.invitations(token,qs.get("store",[""])[0])})
                if post and path=="/memories": return self.result(201,h.memory_put(token,body["store_id"],body["project_id"],body["title"],body["content"],body.get("kind"),body.get("status"),body.get("id"),body.get("expected_version"),source=body.get("source"),tags=body.get("tags"),pinned=body.get("pinned"),archived=body.get("archived"),decision_closed=body.get("decision_closed")))
                if post and path=="/invitations": return self.result(201,h.invite_issue(token,body["store_id"],body["recipient_id"],body["role"],body.get("project_id"),body.get("hours",24)))
                if post and path=="/invitations/accept": return self.result(200,h.invite_accept(token,body["invitation_id"],body["invitation_secret"]))
                if post and path=="/invitations/revoke": return self.result(200,h.invite_revoke(token,body["invitation_id"]))
                if post and path=="/connections": return self.result(201,h.connection_add(token,body["alias"],body["endpoint"],body["expected_identity"]))
                if post and path=="/connections/select": return self.result(200,h.connection_select(token,body["alias"]))
                if post and path=="/connections/remove": return self.result(200,h.connection_remove(token,body["alias"]))
                raise HubError("ROUTE_NOT_FOUND")
            finally:
                h.close()

        def do_GET(self):
            try: self.run_request()
            except HubError as e: self.result(403 if e.code in ("AUTH_REQUIRED","AUTH_DENIED","ACCESS_DENIED","WRONG_RECIPIENT") else 400,{"error":e.code})
            except (KeyError,TypeError,ValueError): self.result(400,{"error":"BAD_REQUEST"})

        def do_POST(self):
            try: self.run_request(post=True)
            except HubError as e: self.result(403 if e.code in ("AUTH_REQUIRED","AUTH_DENIED","ACCESS_DENIED","WRONG_RECIPIENT") else 400,{"error":e.code})
            except (KeyError,TypeError,ValueError): self.result(400,{"error":"BAD_REQUEST"})
    return Handler


def main(argv=None):
    parser=argparse.ArgumentParser(description="Local reference hub; not Sites or OAuth/MCP")
    parser.add_argument("--db",default=os.getenv("BAGO5_MV_DB",str(Path.home()/".bago5"/"memory_hub.sqlite3")))
    subs=parser.add_subparsers(dest="cmd",required=True)
    p=subs.add_parser("user-add");p.add_argument("identity")
    p=subs.add_parser("serve");p.add_argument("--port",type=int,default=8765);p.add_argument("--bind",default="127.0.0.1")
    p=subs.add_parser("store-add");p.add_argument("name")
    p=subs.add_parser("project-add");p.add_argument("store_id");p.add_argument("name")
    p=subs.add_parser("export");p.add_argument("store_id");p.add_argument("destination");p.add_argument("--project-id")
    p=subs.add_parser("import");p.add_argument("store_id");p.add_argument("pack");p.add_argument("--commit",action="store_true")
    p=subs.add_parser("verify-pack");p.add_argument("pack")
    args=parser.parse_args(argv)
    if args.cmd=="serve":
        must(args.bind in ("127.0.0.1","::1","localhost"),"NON_LOOPBACK_DENIED")
        server=ThreadingHTTPServer((args.bind,args.port),make_handler(args.db))
        print(json.dumps({"listening":f"http://{args.bind}:{server.server_port}","scope":"loopback_only","production_deployment":False}),flush=True)
        try:server.serve_forever()
        finally:server.server_close()
        return 0
    h=Hub(args.db)
    try:
        token=os.getenv("BAGO5_MV_TOKEN")
        if args.cmd=="user-add": result={"identity":args.identity,"token_once":h.add_account(args.identity)}
        elif args.cmd=="store-add":result={"store_id":h.store_add(token,args.name)}
        elif args.cmd=="project-add":result={"project_id":h.project_add(token,args.store_id,args.name)}
        elif args.cmd=="export":result=h.pack_export(token,args.store_id,args.destination,args.project_id)
        elif args.cmd=="import":result=h.pack_import(token,args.store_id,args.pack,args.commit)
        elif args.cmd=="verify-pack":
            obj=h._read_pack(args.pack)
            result={"status":"PASS_STRUCTURAL_INTEGRITY","source_store_id":obj["manifest.json"]["source_store_id"],"counts":obj["manifest.json"]["counts"],"authenticity":"NOT_VERIFIED"}
        else: raise HubError("COMMAND_NOT_FOUND")
        print(json.dumps(result,ensure_ascii=False));return 0
    finally:h.close()

if __name__=="__main__":
    try:sys.exit(main())
    except HubError as ex:
        print(json.dumps({"error":ex.code}),file=sys.stderr)
        sys.exit(2)
