"""Create verified complete BAGO5 Windows/Codex distribution from a full release.

Standard library only; no network, hooks, installations or execution.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import tarfile
import tempfile
import zipfile

NAME = "bago5-governed-classic"
MAX_TOTAL = 400 * 1024 * 1024
DEVELOPMENT_ONLY = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def safe_member(name):
    p=PurePosixPath(name.replace("\\","/"))
    return bool(p.parts) and not p.is_absolute() and not any(x in ("..","") for x in p.parts) and ":" not in p.parts[0]

def copy_source(source, dest):
    total=0
    if source.is_dir():
        for p in source.rglob("*"):
            relative=p.relative_to(source)
            if any(part in DEVELOPMENT_ONLY for part in relative.parts) or p.suffix in {".pyc", ".pyo"}:
                continue
            if p.is_symlink(): raise ValueError("Symbolic link rejected: "+str(p))
            if not p.is_file():continue
            if not safe_member(relative.as_posix()):raise ValueError("Invalid path")
            total+=p.stat().st_size
            if total>MAX_TOTAL: raise ValueError("Source too large")
            t=dest/relative;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,t)
    elif tarfile.is_tarfile(source):
        with tarfile.open(source,"r:*") as tar:
            for m in tar:
                if m.isdir(): continue
                if not m.isfile() or not safe_member(m.name):raise ValueError("Unsafe TAR member: "+m.name)
                total+=m.size
                if total>MAX_TOTAL:raise ValueError("Source too large")
                t=dest/PurePosixPath(m.name);t.parent.mkdir(parents=True,exist_ok=True)
                with tar.extractfile(m) as stream,t.open("wb") as f: shutil.copyfileobj(stream,f)
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as z:
            for m in z.infolist():
                if m.is_dir():continue
                if not safe_member(m.filename) or stat.S_ISLNK(m.external_attr>>16):raise ValueError("Unsafe ZIP member")
                total+=m.file_size
                if total>MAX_TOTAL:raise ValueError("Source too large")
                t=dest/PurePosixPath(m.filename);t.parent.mkdir(parents=True,exist_ok=True)
                with z.open(m) as stream,t.open("wb") as f:shutil.copyfileobj(stream,f)
    else:raise ValueError("Source must be a directory, ZIP or tar.gz archive")
    # Archive exporters may place plugin content under one directory.
    if not (dest/"plugin.json").is_file():
        candidates=[p for p in dest.rglob("plugin.json") if p.parent!=dest]
        if len(candidates)!=1:raise ValueError("No unique plugin root in source")
        root=candidates[0].parent
        tmp=dest.parent/"root"
        root.rename(tmp)
        shutil.rmtree(dest);tmp.rename(dest)
    meta=json.loads((dest/"plugin.json").read_text(encoding="utf-8"))
    if meta.get("name")!=NAME: raise ValueError("Wrong plugin identity")
    if not isinstance(meta.get("version"),str) or not meta["version"]:raise ValueError("Missing version")
    if not (dest/"skills/bago5/SKILL.md").is_file():raise ValueError("Main BAGO5 skill missing")
    if not (dest/".codex-plugin/plugin.json").is_file():raise ValueError("Codex manifest missing")
    overlay=json.loads((dest/".codex-plugin/plugin.json").read_text(encoding="utf-8"))
    if overlay.get("name")!=NAME or overlay.get("version")!=meta["version"]: raise ValueError("Manifest mismatch")
    return meta

def build(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    if not source.exists():raise FileNotFoundError(source)
    if output.exists() and any(output.iterdir()):raise FileExistsError("Output directory must be empty")
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bago-dist-") as scratch:
        tree=Path(scratch)/"plugin";tree.mkdir()
        meta=copy_source(source,tree)
        hashes={p.relative_to(tree).as_posix():sha(p) for p in tree.rglob("*") if p.is_file()}
        assert hashes
        manifest={"schema":"bago5-distribution.v1","plugin":NAME,"version":meta["version"],"file_count":len(hashes),"files":dict(sorted(hashes.items()))}
        bundle=output/f"BAGO5_{meta['version']}_CODEX_WINDOWS.zip"
        installer=Path(__file__).resolve().with_name("INSTALAR_BAGO5.ps1")
        if not installer.is_file(): raise FileNotFoundError("Installer script missing")
        with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
            for path in tree.rglob("*"):
                if path.is_file():z.write(path,"plugin/"+path.relative_to(tree).as_posix())
            z.writestr("manifest.sha256.json",json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
            z.write(installer,"INSTALAR_BAGO5.ps1")
            z.writestr("LEEME.txt", "BAGO5 "+meta["version"]+"\nExtraer y ejecutar .\\INSTALAR_BAGO5.ps1 en PowerShell.\nVerificar sin instalar: .\\INSTALAR_BAGO5.ps1 -VerifyOnly\nEl instalador ofrece crear una memoria en ALIFE, conectar existente o continuar sin memoria.\nEl envio del correo se solicita en https://alifememories.com/bago5/activar mediante el formulario del usuario.\nNo se crean Sites ni se envia correo automaticamente. OAuth y lectura se comprueban por anfitrion.\nSin preguntas interactivas: -NoOnboarding. No omitir la inspeccion del paquete.\n")
        with zipfile.ZipFile(bundle) as z:
            assert z.testzip() is None
            for name,digest in hashes.items():
                assert hashlib.sha256(z.read("plugin/"+name)).hexdigest()==digest
        return {"output":str(bundle),"sha256":sha(bundle),"version":meta["version"],"files":len(hashes)}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--source",required=True);parser.add_argument("--output",required=True)
    a=parser.parse_args();print(json.dumps(build(a.source,a.output),ensure_ascii=False,indent=2))
