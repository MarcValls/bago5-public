import hashlib
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/"scripts"/"mv_hub.py"
spec=importlib.util.spec_from_file_location("mv_hub",SOURCE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class HubTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.db=Path(self.t.name)/"store.sqlite"
        self.h=mod.Hub(self.db)
        self.addCleanup(self.h.close)
        self.alice=self.h.add_account("alice")
        self.bob=self.h.add_account("bob")
        self.charlie=self.h.add_account("charlie")
        self.store=self.h.store_add(self.alice,"Owner memory")
        self.p1=self.h.project_add(self.alice,self.store,"Project 1")
        self.p2=self.h.project_add(self.alice,self.store,"Project 2")
        self.m1=self.h.memory_put(self.alice,self.store,self.p1,"Initial","A",kind="decision")
        self.m2=self.h.memory_put(self.alice,self.store,self.p2,"Other","B")

    def denies(self,code,fn,*args,**kw):
        with self.assertRaises(mod.HubError) as cm: fn(*args,**kw)
        self.assertEqual(cm.exception.code,code)

    def invite_bob(self,role="viewer",scope=True):
        invitation=self.h.invite_issue(self.alice,self.store,"bob",role,self.p1 if scope else None)
        grant=self.h.invite_accept(self.bob,invitation["invitation_id"],invitation["token"])
        return invitation,grant

    def test_owner_reader_isolation(self):
        self.assertEqual(self.h.memories(self.bob,self.store),[])
        self.denies("ACCESS_DENIED",self.h.memory_put,self.bob,self.store,self.p1,"bad","bad")
        self.assertEqual(len(self.h.memories(self.alice,self.store)),2)

    def test_invite_requires_authenticated_recipient_and_token(self):
        inv=self.h.invite_issue(self.alice,self.store,"bob","viewer",self.p1)
        self.denies("WRONG_RECIPIENT",self.h.invite_accept,self.charlie,inv["invitation_id"],inv["token"])
        self.denies("INVITATION_SECRET_INVALID",self.h.invite_accept,self.bob,inv["invitation_id"],"bad-token")
        self.assertEqual(len(self.h.memories(self.bob,self.store)),0)
        self.h.invite_accept(self.bob,inv["invitation_id"],inv["token"])
        self.denies("INVITATION_INACTIVE",self.h.invite_accept,self.bob,inv["invitation_id"],inv["token"])
        self.assertEqual(len(self.h.memories(self.bob,self.store)),1)
        self.assertEqual(self.h.memories(self.bob,self.store)[0]["project_id"],self.p1)

    def test_viewer_denied_write_and_other_scope(self):
        self.invite_bob()
        self.denies("ACCESS_DENIED",self.h.memory_put,self.bob,self.store,self.p1,"new","write")
        self.denies("ACCESS_DENIED",self.h.memory_put,self.bob,self.store,self.p2,"new","write")

    def test_editor_can_write_only_granted_project(self):
        self.invite_bob("editor")
        self.h.memory_put(self.bob,self.store,self.p1,"editor","ok")
        self.denies("ACCESS_DENIED",self.h.memory_put,self.bob,self.store,self.p2,"write","denied")

    def test_revoke_invite_also_revokes_grant(self):
        inv,_=self.invite_bob()
        self.assertEqual(len(self.h.memories(self.bob,self.store)),1)
        self.h.invite_revoke(self.alice,inv["invitation_id"])
        self.assertEqual(self.h.memories(self.bob,self.store),[])
        self.denies("ACCESS_DENIED",self.h.invite_revoke,self.bob,inv["invitation_id"])

    def test_revoke_before_accept(self):
        inv=self.h.invite_issue(self.alice,self.store,"bob","editor",self.p1)
        self.h.invite_revoke(self.alice,inv["invitation_id"])
        self.denies("INVITATION_INACTIVE",self.h.invite_accept,self.bob,inv["invitation_id"],inv["token"])

    def test_expired_invite(self):
        inv=self.h.invite_issue(self.alice,self.store,"bob","viewer",self.p1)
        self.h.db.execute("UPDATE invitations SET expires_at='2020-01-01T00:00:00+00:00' WHERE id=?",(inv["invitation_id"],))
        self.denies("INVITATION_EXPIRED",self.h.invite_accept,self.bob,inv["invitation_id"],inv["token"])

    def test_invite_secret_not_persisted(self):
        inv=self.h.invite_issue(self.alice,self.store,"bob","viewer",self.p1)
        self.assertNotIn(inv["token"],json.dumps(self.h.invitations(self.alice,self.store)))
        self.assertNotIn(inv["token"],str(self.h.db.execute("SELECT * FROM invitations WHERE id=?",(inv["invitation_id"],)).fetchone().keys()))
        self.assertNotEqual(inv["token"],self.h._row("SELECT secret_hash FROM invitations WHERE id=?",(inv["invitation_id"],))[0])

    def test_concurrent_version_conflict(self):
        self.h.memory_put(self.alice,self.store,self.p1,"Revised","C",memory_id=self.m1["id"],expected_version=1)
        self.denies("VERSION_CONFLICT",self.h.memory_put,self.alice,self.store,self.p1,"Stale","D",memory_id=self.m1["id"],expected_version=1)
        self.assertEqual(next(m["version"] for m in self.h.memories(self.alice,self.store) if m["id"]==self.m1["id"]),2)

    def test_registry_persistent_and_distinct(self):
        self.h.connection_add(self.alice,"general","https://example.net/mcp","site-general")
        self.h.connection_add(self.alice,"mythos","https://mythos.example.net/mcp","site-mythos")
        self.assertEqual(len(self.h.connections(self.alice)),2)
        self.assertEqual(self.h.connections(self.bob),[])
        self.h.connection_select(self.alice,"mythos")
        self.h.close()
        self.h=mod.Hub(self.db)
        self.addCleanup(self.h.close)
        self.assertEqual(len(self.h.connections(self.alice)),2)
        self.assertEqual([x["alias"] for x in self.h.connections(self.alice) if x["selected"]], ["mythos"])
        self.assertTrue(all(x["state"]=="UNVERIFIED" for x in self.h.connections(self.alice)))
        self.h.connection_remove(self.alice,"mythos")
        self.assertEqual(len(self.h.connections(self.alice)),1)

    def test_connections_reject_alias_reuse_and_secret_url(self):
        self.h.connection_add(self.alice,"general","https://example.net/mcp","site")
        self.denies("ALIAS_ALREADY_EXISTS",self.h.connection_add,self.alice,"general","https://other.net/mcp","other")
        for url in ("http://example.net/mcp","https://user:password@example.net/mcp","https://example.net/mcp?token=abc","https://example.net/mcp#fragment","file:///secret/mcp"):
            self.denies("UNSAFE_MCP_URL",self.h.connection_add,self.alice,"badconnection",url,"site")

    def test_pack_export_import_preview_repeat_and_history(self):
        self.h.memory_put(self.alice,self.store,self.p1,"Updated","Revision two",kind="decision",memory_id=self.m1["id"],expected_version=1)
        pack=Path(self.t.name)/"snapshot.zip"
        r=self.h.pack_export(self.alice,self.store,pack)
        self.assertEqual(r["counts"],dict(projects=2,memories=2,revisions=3))
        with zipfile.ZipFile(pack) as z:
            self.assertEqual(set(z.namelist()),set(mod.MEMBERS))
            allbytes=b"".join(z.read(n) for n in z.namelist())
            self.assertNotIn(self.alice.encode(),allbytes)
        target=self.h.store_add(self.charlie,"Dest memory")
        before=len(self.h.memories(self.charlie,target))
        plan=self.h.pack_import(self.charlie,target,pack,commit=False)
        self.assertEqual(plan["memories_created"],2)
        self.assertEqual(before,len(self.h.memories(self.charlie,target)))
        result=self.h.pack_import(self.charlie,target,pack,commit=True)
        self.assertEqual(result["memories_created"],2)
        result2=self.h.pack_import(self.charlie,target,pack,commit=True)
        self.assertEqual(result2["memories_skipped"],2)
        self.assertEqual(len(self.h.memories(self.charlie,target)),2)
        self.assertEqual(self.h.db.execute("SELECT COUNT(*) FROM revisions WHERE memory_id IN (SELECT id FROM memories WHERE store_id=?)",(target,)).fetchone()[0],3)

    def test_viewer_can_export_only_shared_scope(self):
        self.invite_bob()
        self.denies("ACCESS_DENIED",self.h.pack_export,self.bob,self.store,Path(self.t.name)/"full.zip")
        result=self.h.pack_export(self.bob,self.store,Path(self.t.name)/"partial.zip",self.p1)
        self.assertEqual(result["counts"]["memories"],1)

    def test_pack_tamper_rejected(self):
        pack=Path(self.t.name)/"snapshot.zip"
        self.h.pack_export(self.alice,self.store,pack)
        with zipfile.ZipFile(pack) as src:
            data={name:src.read(name) for name in src.namelist()}
        data["memories.json"]=data["memories.json"].replace(b"Initial",b"Changed")
        tampered=Path(self.t.name)/"tampered.zip"
        with zipfile.ZipFile(tampered,"w") as z:
            for n,v in data.items(): z.writestr(n,v)
        target=self.h.store_add(self.charlie,"T")
        self.denies("HASH_MISMATCH",self.h.pack_import,self.charlie,target,tampered,True)
        self.assertEqual(len(self.h.memories(self.charlie,target)),0)

    def test_pack_extra_path_rejected(self):
        path=Path(self.t.name)/"unsafe.zip"
        with zipfile.ZipFile(path,"w") as z:z.writestr("../../secrets.txt","bad")
        self.denies("PACK_MEMBER_INVALID",mod.Hub._read_pack,path)

    def test_import_conflict_is_atomic(self):
        pack=Path(self.t.name)/"snapshot.zip"
        self.h.pack_export(self.alice,self.store,pack)
        target=self.h.store_add(self.charlie,"dest")
        self.h.pack_import(self.charlie,target,pack,commit=True)
        mid=self.h.db.execute("SELECT id,project_id FROM memories WHERE store_id=? AND origin_key LIKE ?",(target,self.store+'::%')).fetchone()
        self.h.memory_put(self.charlie,target,mid["project_id"],"Custom","local fork",memory_id=mid["id"],expected_version=1)
        self.denies("IMPORT_CONFLICT",self.h.pack_import,self.charlie,target,pack,True)
        self.assertEqual(len(self.h.memories(self.charlie,target)),2)

    def test_metadata_preserved_in_pack_and_history(self):
        m=self.h.memory_put(self.alice,self.store,self.p1,"Decision","adopted",kind="decision",source="contract:v1",tags=["scope","verified"],pinned=True,archived=True,decision_closed=True)
        pack=Path(self.t.name)/"metadata.zip"
        self.h.pack_export(self.alice,self.store,pack)
        target=self.h.store_add(self.charlie,"target")
        self.h.pack_import(self.charlie,target,pack,commit=True)
        rec=next(x for x in self.h.memories(self.charlie,target) if x["title"]=="Decision")
        self.assertEqual(rec["source"],"contract:v1")
        self.assertEqual(rec["tags"],["scope","verified"])
        self.assertTrue(rec["pinned"] and rec["archived"] and rec["decision_closed"])
        hist=self.h._row("SELECT snapshot FROM revisions WHERE memory_id=?",(rec["id"],))
        snap=json.loads(hist["snapshot"])
        self.assertTrue(snap["decision_closed"])
        self.assertEqual(snap["source"],"contract:v1")

    def test_update_preserves_unspecified_metadata(self):
        m=self.h.memory_put(self.alice,self.store,self.p1,"Base","1",kind="decision",source="contract",tags=["keep"],pinned=True,archived=True,decision_closed=True)
        self.h.memory_put(self.alice,self.store,self.p1,"Base revised","2",kind="decision",memory_id=m["id"],expected_version=1)
        rec=next(x for x in self.h.memories(self.alice,self.store) if x["id"]==m["id"])
        self.assertEqual(rec["source"],"contract")
        self.assertEqual(rec["tags"],["keep"])
        self.assertTrue(rec["pinned"] and rec["archived"] and rec["decision_closed"])

    def test_update_preserves_kind_and_status(self):
        m=self.h.memory_put(self.alice,self.store,self.p1,"Decision","1",kind="decision",status="pending")
        self.h.memory_put(self.alice,self.store,self.p1,"Decision edited","2",memory_id=m["id"],expected_version=1)
        rec=next(x for x in self.h.memories(self.alice,self.store) if x["id"]==m["id"])
        self.assertEqual((rec["kind"],rec["status"]),("decision","pending"))

    def test_origin_provenance_transitive_through_two_imports(self):
        p1=Path(self.t.name)/"p1.zip"
        self.h.pack_export(self.alice,self.store,p1)
        second=self.h.store_add(self.charlie,"second")
        self.h.pack_import(self.charlie,second,p1,commit=True)
        p2=Path(self.t.name)/"p2.zip"
        self.h.pack_export(self.charlie,second,p2)
        third=self.h.store_add(self.bob,"third")
        self.h.pack_import(self.bob,third,p2,commit=True)
        rec=self.h.memories(self.bob,third)
        self.assertTrue(all(x["origin_key"].startswith(self.store+"::") for x in rec))

    def test_import_requires_store_owner(self):
        self.invite_bob("editor")
        pack=Path(self.t.name)/"source.zip"
        self.h.pack_export(self.alice,self.store,pack)
        self.denies("ACCESS_DENIED",self.h.pack_import,self.bob,self.store,pack,True)

    def test_recomputed_hash_cannot_hide_snapshot_mismatch(self):
        pack=Path(self.t.name)/"source.zip"
        self.h.pack_export(self.alice,self.store,pack)
        with zipfile.ZipFile(pack) as z:
            data={n:z.read(n) for n in z.namelist()}
        records=json.loads(data["memories.json"])
        records[0]["content"]="fabricated"
        data["memories.json"]=mod.json_bytes(records)
        hashes="".join(f"{mod.digest(v)}  {n}\n" for n,v in sorted(data.items()) if n!="SHA256SUMS.txt")
        data["SHA256SUMS.txt"]=hashes.encode("ascii")
        bad=Path(self.t.name)/"fabricated.zip"
        with zipfile.ZipFile(bad,"w") as z:
            for n,v in data.items(): z.writestr(n,v)
        self.denies("SNAPSHOT_MISMATCH",mod.Hub._read_pack,bad)

    def test_http_invite_flow_requires_authentication(self):
        server=mod.ThreadingHTTPServer(("127.0.0.1",0),mod.make_handler(self.db))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f"http://127.0.0.1:{server.server_port}"
        def post(path,token,data):
            req=urllib.request.Request(base+path,method="POST",data=json.dumps(data).encode(),headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
            try:
                with urllib.request.urlopen(req,timeout=2) as resp:return resp.status,json.loads(resp.read())
            except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
        code,invite=post("/invitations",self.alice,{"store_id":self.store,"project_id":self.p1,"recipient_id":"bob","role":"viewer"})
        self.assertEqual(code,201)
        self.assertEqual(post("/invitations/accept",self.charlie,{"invitation_id":invite["invitation_id"],"invitation_secret":invite["token"]})[0],403)
        self.assertEqual(post("/invitations/accept",self.bob,{"invitation_id":invite["invitation_id"],"invitation_secret":invite["token"]})[0],200)
        self.assertEqual(len(self.h.memories(self.bob,self.store)),1)
        self.assertEqual(post("/invitations/revoke",self.alice,{"invitation_id":invite["invitation_id"]})[0],200)
        self.assertEqual(len(self.h.memories(self.bob,self.store)),0)

    def test_http_boundary_enforces_auth(self):
        server=mod.ThreadingHTTPServer(("127.0.0.1",0),mod.make_handler(self.db))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f"http://127.0.0.1:{server.server_port}"
        def get(path,token=None):
            req=urllib.request.Request(base+path,headers={"Authorization":"Bearer "+token} if token else {})
            try:
                with urllib.request.urlopen(req,timeout=2) as resp:
                    return resp.status,json.loads(resp.read())
            except urllib.error.HTTPError as e:
                return e.code,json.loads(e.read())
        self.assertEqual(get("/health")[0],200)
        self.assertEqual(get("/stores")[0],403)
        self.assertEqual(get("/memories?store="+self.store,self.bob)[1]["memories"],[])
        self.invite_bob()
        self.assertEqual(len(get("/memories?store="+self.store,self.bob)[1]["memories"]),1)
        self.assertEqual(len(get("/memories?store="+self.store,self.alice)[1]["memories"]),2)


if __name__=="__main__": unittest.main()
