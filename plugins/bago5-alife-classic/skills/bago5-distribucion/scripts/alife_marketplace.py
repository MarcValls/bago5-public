#!/usr/bin/env python3
"""ALIFE catalog client: explicit local config, read-only queries, verified download.

No credentials, server writes, installation, migration or code execution. Registry
compatibility is a declaration; an artifact hash does not prove runtime behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ORIGIN = "https://alifememories.com"
CONFIG = {
    "schema": "bago5.alife-marketplace.v1",
    "canonical_origin": ORIGIN,
    "catalog_url": ORIGIN + "/api/templates",
    "compatibility_url": ORIGIN + "/api/templates/compatibility",
    "activation_url": ORIGIN + "/bago5/activar",
}
KEYS = ("template_id", "version", "component_id", "component_version",
        "contract_id", "contract_version", "schema_version")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
MAX_JSON = 2 * 1024 * 1024
MAX_ARTIFACT = 400 * 1024 * 1024


class CatalogError(ValueError):
    pass


def no_links(path):
    path = Path(path)
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise CatalogError("LINK_PATH_REJECTED")


def parse_json(raw):
    if len(raw) > MAX_JSON:
        raise CatalogError("JSON_TOO_LARGE")
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise CatalogError("DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    def constant(_):
        raise CatalogError("NONFINITE_JSON")
    obj = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(obj, dict):
        raise CatalogError("JSON_OBJECT_REQUIRED")
    return obj


def read_json(path):
    path = Path(path)
    no_links(path)
    if not path.is_file() or path.stat().st_size > MAX_JSON:
        raise CatalogError("INVALID_JSON_FILE")
    with path.open("rb") as stream:
        return parse_json(stream.read(MAX_JSON + 1))


def validate_config(value):
    if value != CONFIG:
        raise CatalogError("CONFIG_CONFLICT_OR_UNSUPPORTED_SCHEMA")
    return value


def configure(path):
    path = Path(path)
    no_links(path)
    if path.exists():
        validate_config(read_json(path))
        return {"status": "UNCHANGED", "config": str(path), "remote_access": "NOT_RUN"}
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(CONFIG, ensure_ascii=False, indent=2) + "\n")
    except FileExistsError:
        validate_config(read_json(path))
        return {"status": "UNCHANGED", "config": str(path), "remote_access": "NOT_RUN"}
    return {"status": "CONFIGURED", "config": str(path), "remote_access": "NOT_RUN"}


def safe_url(value, *, query=False):
    if not isinstance(value, str) or len(value) > 4096 or any(ord(x) < 32 for x in value):
        raise CatalogError("INVALID_CANONICAL_URL")
    url = urllib.parse.urlsplit(value)
    if (url.scheme != "https" or url.netloc != "alifememories.com"
            or url.username or url.password or url.fragment or (url.query and not query)):
        raise CatalogError("NON_CANONICAL_URL")
    if not url.path.startswith("/") or "\\" in url.path:
        raise CatalogError("INVALID_CANONICAL_PATH")
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise CatalogError("REDIRECT_REQUIRES_REVALIDATION")


def request(url, *, query=False):
    safe_url(url, query=query)
    opener = urllib.request.build_opener(NoRedirect())
    return opener.open(urllib.request.Request(url, headers={"Accept": "application/json, application/octet-stream"}), timeout=20)


def get_json(url):
    with request(url, query=True) as response:
        if response.headers.get_content_type() != "application/json":
            raise CatalogError("JSON_RESPONSE_REQUIRED")
        return parse_json(response.read(MAX_JSON + 1))


def validate_release(response, expected):
    if response.get("canonical_origin") != ORIGIN:
        raise CatalogError("CATALOG_ORIGIN_MISMATCH")
    release = response.get("template")
    if not isinstance(release, dict):
        raise CatalogError("RELEASE_REQUIRED")
    for key in ("template_id", "version"):
        if release.get(key) != expected[key]:
            raise CatalogError("RELEASE_IDENTITY_MISMATCH")
    if release.get("status") != "PUBLISHED":
        raise CatalogError("RELEASE_NOT_PUBLISHED")
    manifest = release.get("manifest")
    if (not isinstance(manifest, dict)
            or manifest.get("template_id") != expected["template_id"]
            or manifest.get("version") != expected["version"]):
        raise CatalogError("MANIFEST_IDENTITY_MISMATCH")
    if not SHA256.fullmatch(str(release.get("package_sha256", ""))):
        raise CatalogError("ARTIFACT_HASH_REQUIRED")
    safe_url(release.get("package_url"))
    return release


def validate_compatibility(response, expected):
    if response.get("canonical_origin") != ORIGIN:
        raise CatalogError("CATALOG_ORIGIN_MISMATCH")
    for key in KEYS:
        if response.get(key) != expected[key]:
            raise CatalogError("EXACT_COMPATIBILITY_MISMATCH:" + key)
    if response.get("installed_schema_version") != expected.get("installed_schema_version"):
        raise CatalogError("INSTALLED_SCHEMA_MISMATCH")
    if (response.get("compatible") is not True or response.get("status") != "PASS"
            or response.get("release_status") != "PUBLISHED" or response.get("action") != "ALLOW"):
        raise CatalogError("COMPATIBILITY_NOT_ALLOWED")
    safe_url(response.get("evidence_ref"))
    if not SHA256.fullmatch(str(response.get("evidence_sha256", ""))):
        raise CatalogError("COMPATIBILITY_EVIDENCE_HASH_REQUIRED")
    if not isinstance(response.get("checked_at"), str) or not response["checked_at"].strip():
        raise CatalogError("COMPATIBILITY_DATE_REQUIRED")
    return response


def verify(release_response, compatibility_response, expected):
    for key in KEYS:
        val = expected.get(key)
        if not isinstance(val, str) or not val or val != val.strip() or len(val) > 120:
            raise CatalogError("EXACT_SELECTION_REQUIRED:" + key)
    release = validate_release(release_response, expected)
    validate_compatibility(compatibility_response, expected)
    return {"status": "ELIGIBLE_ACCORDING_TO_REGISTRY", "selection": expected,
            "package_url": release["package_url"], "package_sha256": release["package_sha256"],
            "evidence_ref": compatibility_response["evidence_ref"],
            "evidence_sha256": compatibility_response["evidence_sha256"],
            "execution": "NOT_RUN", "installation": "NOT_RUN"}


def list_catalog(config):
    validate_config(config)
    response = get_json(config["catalog_url"])
    if (response.get("canonical_origin") != ORIGIN
            or type(response.get("catalog_version")) is not int or response["catalog_version"] != 1):
        raise CatalogError("UNSUPPORTED_CATALOG")
    rows = response.get("templates")
    if not isinstance(rows, list):
        raise CatalogError("CATALOG_RELEASES_REQUIRED")
    return {"canonical_origin": ORIGIN, "templates": rows, "installation": "NOT_RUN",
            "note": "PUBLISHED still requires exact compatibility and artifact verification"}


def check(config, expected):
    validate_config(config)
    release_url = config["catalog_url"] + "/" + "/".join(urllib.parse.quote(expected[x], safe="") for x in ("template_id", "version"))
    compatibility_url = config["compatibility_url"] + "?" + urllib.parse.urlencode(expected)
    return verify(get_json(release_url), get_json(compatibility_url), expected)


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(eligibility, output):
    if eligibility.get("status") != "ELIGIBLE_ACCORDING_TO_REGISTRY":
        raise CatalogError("REGISTRY_CHECK_REQUIRED")
    url = safe_url(eligibility.get("package_url"))
    digest = eligibility.get("package_sha256", "")
    if not SHA256.fullmatch(digest):
        raise CatalogError("ARTIFACT_HASH_REQUIRED")
    output = Path(output)
    no_links(output)
    if output.exists():
        if not output.is_file() or output.stat().st_size > MAX_ARTIFACT or file_hash(output) != digest:
            raise CatalogError("OUTPUT_CONFLICT")
        return {"status": "ALREADY_PRESENT", "output": str(output), "sha256": digest, "installation": "NOT_RUN"}
    if not output.parent.is_dir():
        raise CatalogError("OUTPUT_DIRECTORY_REQUIRED")
    temporary = None
    try:
        with request(url) as response, tempfile.NamedTemporaryFile(dir=output.parent, prefix=".bago-download-", delete=False) as stream:
            temporary = Path(stream.name)
            h = hashlib.sha256()
            size = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ARTIFACT:
                    raise CatalogError("ARTIFACT_TOO_LARGE")
                h.update(chunk)
                stream.write(chunk)
            if h.hexdigest() != digest:
                raise CatalogError("ARTIFACT_HASH_MISMATCH")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError:
            no_links(output)
            if not output.is_file() or file_hash(output) != digest:
                raise CatalogError("OUTPUT_CONFLICT")
        return {"status": "DOWNLOADED_VERIFIED", "output": str(output), "sha256": digest,
                "bytes": size, "installation": "NOT_RUN", "execution": "NOT_RUN"}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("configure", "list", "check", "download", "verify"):
        child = sub.add_parser(cmd)
        if cmd != "verify":
            child.add_argument("--config", type=Path, required=True)
        if cmd in ("check", "download", "verify"):
            for key in KEYS:
                child.add_argument("--" + key.replace("_", "-"), required=True)
            child.add_argument("--installed-schema-version")
        if cmd == "verify":
            child.add_argument("--release", type=Path, required=True)
            child.add_argument("--compatibility", type=Path, required=True)
        if cmd == "download":
            child.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "configure":
            result = configure(args.config)
        elif args.command == "list":
            result = list_catalog(read_json(args.config))
        else:
            expected = {key: getattr(args, key) for key in KEYS}
            if args.installed_schema_version is not None:
                expected["installed_schema_version"] = args.installed_schema_version
            if args.command == "verify":
                result = verify(read_json(args.release), read_json(args.compatibility), expected)
            else:
                result = check(read_json(args.config), expected)
                if args.command == "download":
                    result = download(result, args.output)
    except (OSError, ValueError, KeyError, TypeError, RecursionError, urllib.error.URLError) as exc:
        # Do not echo URLs, headers, response bodies or arbitrary transport errors.
        reason = str(exc) if isinstance(exc, CatalogError) else type(exc).__name__
        print(json.dumps({"status": "BLOCKED", "reason": reason, "installation": "NOT_RUN"}))
        return 3
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
