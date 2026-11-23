# Design System BAGO

Fuente: `bago_fw/ui-react/src/styles.css` (`:root`). **Single source of truth**.

## Paleta

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#050813` | Fondo app |
| `--bg2` | `#08101f` | Fondo secundario |
| `--panel` | `#0f172a` | Panel base |
| `--panel2` | `#121d32` | Panel elevado |
| `--panel3` | `#17233d` | Panel hover/activo |
| `--line` | `rgba(148,163,184,.17)` | Bordes sutiles |
| `--line2` | `rgba(148,163,184,.28)` | Bordes enfatizados |
| `--text` | `#e8eefb` | Texto principal |
| `--muted` | `#91a5c0` | Texto secundario (AA OK sobre panel) |
| `--muted2` | `#64748b` | Placeholder/disabled (NO texto de lectura) |
| `--brand` | `#7c8cff` | Acento principal (indigo) |
| `--brand-strong` | `#4658ff` | Acento hover/press |
| `--cyan` | `#22d3ee` | Acento secundario |
| `--ok` | `#34d399` | Estado OK / verde |
| `--warn` | `#fbbf24` | Aviso / amarillo |
| `--danger` | `#fb7185` | Error / rojo |
| `--violet` | `#c084fc` | Decorativo |
| `--orange` | `#fb923c` | Decorativo |

## Aliases (compat)

`--sidebar`= `--panel` · `--accent`= `--brand` · `--hover`= `rgba(148,163,184,.08)` · `--soft`= `rgba(148,163,184,.06)`

## Tipografía

- Sans: `"Inter","Segoe UI Variable","Aptos",system-ui,sans-serif`
- Mono: `"JetBrains Mono","Cascadia Code",SFMono-Regular,Consolas,monospace`
- `font-synthesis: none`, `text-rendering: optimizeLegibility`

## Espaciado / forma

- `--radius: 20px` (cards/panels) · chips `calc(var(--radius)*.6)`
- `--shadow: 0 26px 90px rgba(0,0,0,.45)` (overlays/modals)
- Base responsive `min-width: 320px`

## Backgrounds

`body` lleva 3 radial-gradients (brand/cyan/ok) + linear gradient. **No duplicar** en panels: usar `--panel` sólido.

## Componentes base

- **Panel**: `background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius)`
- **Chip/Tag**: `var(--soft)` bg, `var(--muted)` text, `calc(var(--radius)*.6)` radius
- **Botón primario**: `var(--brand)` bg, `var(--text)` fg, hover `var(--brand-strong)`
- **Botón ghost**: transparent bg, `var(--line)` border, hover `var(--hover)`

## Capas z-index (acordadas)

| Capa | z-index | Uso |
|---|---|---|
| base | 1 | panels, vistas |
| dropdown | 50 | SlashMenu, selectores |
| overlay | 100 | ManagerOverlay, docks |
| toast | 200 | Toast.jsx |
| modal | 300 | modales full-screen |

## Vistas (control-plane/views/)

`DashboardView`, `AuditView`, `HealthView`, `InstallationsView`, `NodesView`, `PatchbayView`, `PiecesView`, `ReleasesView` + `components/PlanSequencer.jsx`.

Cada vista debe:
- Recibir datos por props o hooks (`useManagerContext`, `useBagoControl`, `usePipelineNodes`)
- No importar CSS global nuevo; estilizar en `control-plane.css`/`.codex.css`
- Definir estados loading / error / vacío

## Iconos

`control-plane/icons.jsx` exporta SVG inline. Decorativos → `aria-hidden="true"`. Semánticos → `role="img"` + `aria-label`.

## Reglas estrictas

1. **No hardcoded colors** en JSX. Usar `style={{ color: 'var(--muted)' }}` o clases.
2. **No nuevas deps UI** (Tailwind/MUI/etc). Solo React + CSS.
3. **No z-index mágicos**: respetar tabla de capas.
4. **No overflow-x**: hijos flex → `min-width: 0`. Grid → `repeat(auto-fit, minmax(280px, 1fr))`.
5. **No botones decorativos**: sin `onClick` real → `TODO:` visible o no renderizar.