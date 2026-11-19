"""Compara los archivos solicitados en dos directorios sin modificarlos."""
import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(root, relative):
    target = (root / relative).resolve()
    target.relative_to(root)
    if not target.is_file():
        return None
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    roots = [path.resolve() for path in (args.source, args.destination)]
    if not all(root.is_dir() for root in roots):
        parser.error("Se requieren dos directorios existentes.")
    rows = []
    for path in args.files:
        if path.anchor or ".." in path.parts:
            parser.error("Cada archivo debe ser una ruta relativa dentro de ambos directorios.")
        try:
            left, right = [fingerprint(root, path) for root in roots]
        except (OSError, ValueError):
            parser.error("No se puede leer un archivo dentro de las raíces indicadas.")
        if left is None or right is None:
            status = "MISSING"
        elif left == right:
            status = "MATCH"
        else:
            status = "DIFF"
        rows.append({"file": path.as_posix(), "source": left, "destination": right, "status": status})
    print(json.dumps(rows, indent=2))
    return int(any(row["status"] != "MATCH" for row in rows))


if __name__ == "__main__":
    raise SystemExit(main())
