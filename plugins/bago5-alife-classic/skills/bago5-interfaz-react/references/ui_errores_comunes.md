# Errores UI comunes en BAGO

8 problemas frecuentes con síntoma, causa y fix.

## 1. Pantalla blanca en Electron

**Síntoma**: `manager:dev` abre ventana blanca sin UI.

**Causa**: `ui-react/dist/` vacío o desactualizado; Electron carga `dist/index.html` inexistente.

**Fix**:
```bash
cd /d C:\Users\AMTEC_Terminal_1º\bago_fw
npm run manager:build-ui
npm run manager:dev
```
Verificar `electron/main.cjs` apunta a `path.join(__dirname,'ui-react','dist','index.html')`.

## 2. CSS no aplica tras editar styles.css

**Síntoma**: Cambios en tokens no se reflejan.

**Causa**: Vite cachea; o `main.jsx` no importa la hoja correcta.

**Fix**:
```powershell
Remove-Item -Recurse -Force "ui-react\node_modules\.vite-temp" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "ui-react\dist" -ErrorAction SilentlyContinue
npm run manager:build-ui
```
Verificar `ui-react/src/main.jsx` → `import './styles.css'` y `ControlPlane.jsx` → `import './control-plane.css'`.

## 3. Overlay queda "pegado" / no cierra

**Síntoma**: `ManagerOverlay` o `SlashMenu` no desaparece al hacer clic fuera.

**Causa**: Falta handler en backdrop o `pointer-events: none` en backdrop.

**Fix**: backdrop con `onClick={onClose}` y `pointer-events: auto`. Contenido con `e.stopPropagation()`. Esc vía `useEffect` con listener `keydown`.

## 4. Scroll horizontal aparece

**Síntoma**: Scroll-x visible a 1280px o 1920px.

**Causa**: Hijo flex con `min-width: max-content` o grid con columnas fijas > viewport.

**Fix**: padre flex → `min-width: 0` en hijos. Grid → `grid-template-columns: repeat(auto-fit, minmax(280px,1fr))`. `body { overflow: hidden }` ya está; el problema está dentro de panels.

## 5. Texto ilegible (bajo contraste)

**Síntoma**: `--muted2` (#64748b) sobre `--panel` da <4.5:1.

**Causa**: `--muted2` es para placeholders/disabled, no texto de lectura.

**Fix**: usar `--muted` (#91a5c0) para texto secundario. `--muted2` solo en hints/disabled. Validar con `ui_audit.py --contrast`.

## 6. Build vite falla por import circular

**Síntoma**: `vite build` → `Cannot use import statement outside a module` o circular dep.

**Causa**: `ControlPlane.jsx` importa una vista que importa `ControlPlane` (para datos compartidos).

**Fix**: extraer datos a `control-plane/data.js` / `planData.js` (ya existen). Vistas importan data, no al padre.

## 7. z-index war (overlay detrás de panel)

**Síntoma**: Modal aparece bajo dropdown o panel.

**Causa**: z-index hardcoded dispersos.

**Fix**: capas acordadas → base 1, dropdown 50, overlay 100, toast 200, modal 300. Auditar con `ui_audit.py --zindex`.

## 8. Iconos sin accesibilidad

**Síntoma**: Screen reader anuncia "image" sin contexto.

**Causa**: SVG inline sin `aria-hidden` ni `role`.

**Fix**: decorativo → `<svg aria-hidden="true" ...>`. Semántico → `<svg role="img" aria-label="Cerrar" ...>`.