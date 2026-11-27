#!/usr/bin/env python3
"""
ui_audit.py — Auditoría estática de la UI de BAGO (Electron+React+Vite).

Uso:
    python ui_audit.py "<perfil-local>\\bago_fw\\ui-react\\src"
    python ui_audit.py "C:\\...\\ui-react\\src" --contrast
    python ui_audit.py "C:\\...\\ui-react\\src" --zindex
    python ui_audit.py "C:\\...\\ui-react\\src" --unused-css
    python ui_audit.py "C:\\...\\ui-react\\src" --hardcoded

Sin flags ejecuta todos los checks. Salida: texto legible + archivo
ui_audit_report.md junto al src escaneado.
"""
import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

JSX_EXT = {".jsx", ".js"}
CSS_EXT = {".css"}

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}){1,2}\b")
RGB_RE = re.compile(r"rgba?\(\s*\d", re.I)
Z_RE = re.compile(r"z-index\s*:\s*(\d+)", re.I)
IMPORT_RE = re.compile(
    r"""^\s*import(?:\s+[^'"]+from)?\s+['"]([^'"]+)['"]\s*;?""", re.M
)
CLASS_USE_RE = re.compile(r"""className\s*=\s*["'`]([^"'`]+)["'`]""")
CSS_CLASS_DEF_RE = re.compile(r"""\.([A-Za-z_][\w-]*)""")

# pares texto/fondo a chequear contraste AA (>=4.5:1 para texto normal)
CONTRAST_PAIRS = [
    ("#e8eefb", "#0f172a", "--text/--panel"),
    ("#91a5c0", "#0f172a", "--muted/--panel"),
    ("#64748b", "#0f172a", "--muted2/--panel (¡alerta!)"),
    ("#e8eefb", "#050813", "--text/--bg"),
    ("#91a5c0", "#050813", "--muted/--bg"),
    ("#64748b", "#050813", "--muted2/--bg (¡alerta!)"),
    ("#e8eefb", "#121d32", "--text/--panel2"),
    ("#91a5c0", "#121d32", "--muted/--panel2"),
    ("#64748b", "#121d32", "--muted2/--panel2 (¡alerta!)"),
]


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def _contrast(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def scan_files(root: Path):
    jsx_files, css_files = [], []
    for dirpath, _dirs, files in os.walk(root):
        # ignorar node_modules / dist / .vite-temp
        if any(seg in dirpath for seg in ("node_modules", "dist", ".vite-temp", "__pycache__")):
            continue
        for f in files:
            p = Path(dirpath) / f
            if p.suffix in JSX_EXT:
                jsx_files.append(p)
            elif p.suffix in CSS_EXT:
                css_files.append(p)
    return jsx_files, css_files


def check_hardcoded_colors(jsx_files):
    hits = []
    for p in jsx_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for ln, line in enumerate(txt.splitlines(), 1):
            if "var(--" in line:
                continue
            # colores en style={{...}} o strings
            for m in HEX_RE.finditer(line):
                hits.append((str(p), ln, m.group(0), line.strip()[:120]))
            for m in RGB_RE.finditer(line):
                if "rgba(0,0,0,0)" not in line.replace(" ", ""):
                    hits.append((str(p), ln, m.group(0), line.strip()[:120]))
    return hits


def check_circular_imports(jsx_files):
    # grafo simple por archivo
    graph = defaultdict(set)
    file_set = {p.resolve() for p in jsx_files}
    for p in jsx_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in IMPORT_RE.finditer(txt):
            spec = m.group(1)
            if spec.startswith(".") or spec.startswith(".."):
                target = (p.parent / spec).resolve()
                for ext in ("", ".jsx", ".js", "/index.jsx", "/index.js"):
                    cand = Path(str(target) + ext) if ext else target
                    if cand.resolve() in file_set:
                        graph[p.resolve()].add(cand.resolve())
                        break
    # DFS para detectar ciclo
    cycles = []

    def dfs(node, stack, visited_local):
        if node in stack:
            idx = stack.index(node)
            cycles.append(stack[idx:] + [node])
            return
        if node in visited_local:
            return
        visited_local.add(node)
        for nxt in graph.get(node, ()):
            dfs(nxt, stack + [node], visited_local)

    seen = set()
    for n in graph:
        if n not in seen:
            dfs(n, [], set())
            seen.add(n)
    # dedup
    uniq = []
    norm = set()
    for c in cycles:
        key = tuple(sorted(c[:-1]))
        if key not in norm:
            norm.add(key)
            uniq.append(c)
    return uniq


def check_unused_css(css_files, jsx_files):
    used = set()
    for p in jsx_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in CLASS_USE_RE.finditer(txt):
            for cls in m.group(1).split():
                used.add(cls)
    unused = []
    for p in css_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in CSS_CLASS_DEF_RE.finditer(txt):
            cls = m.group(1)
            # clases tipo estado BEM __ o -- pueden no aparecer literalmente
            base = cls.split("__")[0].split("--")[0]
            if cls not in used and base not in used and not cls.startswith("_"):
                unused.append((str(p), cls))
    return unused


def check_zindex(css_files, jsx_files):
    z_map = []
    for p in css_files + jsx_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for ln, line in enumerate(txt.splitlines(), 1):
            for m in Z_RE.finditer(line):
                z_map.append((str(p), ln, int(m.group(1))))
    # fuera de capas acordadas (1,50,100,200,300) + rangos razonables
    accepted = {1, 2, 3, 10, 50, 100, 200, 300}
    orphans = [(p, ln, z) for p, ln, z in z_map if z not in accepted]
    return z_map, orphans


def check_contrast():
    rows = []
    for fg, bg, label in CONTRAST_PAIRS:
        ratio = _contrast(fg, bg)
        status = "AA OK" if ratio >= 4.5 else "AA FAIL"
        rows.append((label, fg, bg, round(ratio, 2), status))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--contrast", action="store_true")
    ap.add_argument("--zindex", action="store_true")
    ap.add_argument("--unused-css", action="store_true")
    ap.add_argument("--hardcoded", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"NO existe: {root}", file=sys.stderr)
        sys.exit(1)

    run_all = not (args.contrast or args.zindex or args.unused_css or args.hardcoded)
    jsx_files, css_files = scan_files(root)

    out = []
    out.append("# Auditoría UI BAGO\n")
    out.append(f"Raíz: `{root}`\n")
    out.append(f"Archivos JSX/JS: {len(jsx_files)} | CSS: {len(css_files)}\n\n")

    if run_all or args.hardcoded:
        out.append("## Colores hardcoded en JSX (deben usar var(--*))\n")
        hits = check_hardcoded_colors(jsx_files)
        if hits:
            for p, ln, color, line in hits[:40]:
                out.append(f"- `{p}:{ln}` `{color}` → `{line}`")
            if len(hits) > 40:
                out.append(f"- ...y {len(hits)-40} más")
        else:
            out.append("- (ninguno) ✔")
        out.append("")

    if run_all:
        out.append("## Imports circulares\n")
        cyc = check_circular_imports(jsx_files)
        if cyc:
            for c in cyc:
                out.append("- " + " → ".join(Path(x).name for x in c))
        else:
            out.append("- (ninguno) ✔")
        out.append("")

    if run_all or args.unused_css:
        out.append("## Selectores CSS posiblemente sin uso\n")
        unused = check_unused_css(css_files, jsx_files)
        if unused:
            for p, cls in unused[:60]:
                out.append(f"- `{p}` → `.{cls}`")
            if len(unused) > 60:
                out.append(f"- ...y {len(unused)-60} más")
        else:
            out.append("- (ninguno) ✔")
        out.append("")

    if run_all or args.zindex:
        out.append("## z-index\n")
        z_map, orphans = check_zindex(css_files, jsx_files)
        out.append(f"Total z-index declarados: {len(z_map)}")
        out.append("Capas acordadas: base=1, dropdown=50, overlay=100, toast=200, modal=300\n")
        if orphans:
            out.append("**Fuera de capas acordadas:**")
            for p, ln, z in orphans:
                out.append(f"- `{p}:{ln}` z-index={z}")
        else:
            out.append("- todos en capas acordadas ✔")
        out.append("")

    if run_all or args.contrast:
        out.append("## Contraste WCAG AA (texto normal ≥ 4.5:1)\n")
        rows = check_contrast()
        out.append("| Par | FG | BG | Ratio | Estado |")
        out.append("|---|---|---|---|---|")
        for label, fg, bg, ratio, status in rows:
            out.append(f"| {label} | {fg} | {bg} | {ratio} | {status} |")
        out.append("")

    report = "\n".join(out)
    print(report)
    out_path = root.parent / "ui_audit_report.md"
    try:
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[reporte guardado] {out_path}", file=sys.stderr)
    except Exception as e:
        print(f"[no se pudo guardar reporte] {e}", file=sys.stderr)


if __name__ == "__main__":
    main()