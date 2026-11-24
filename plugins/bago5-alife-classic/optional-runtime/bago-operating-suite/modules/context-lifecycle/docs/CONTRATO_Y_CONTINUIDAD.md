# CONTINUIDAD — BAGO5os Context Lifecycle LAB-RC2 (2026-10-29)

## Alcance y procedencia

Base inmutable: `BAGO5os_1.4.6_SESSION_CONTEXT_RC1.zip` (SHA-256 registrado en
`FILE_LOCK.json`); 653 entradas. Se conserva un único ejemplar y se extrae en
TemporalDirectory solo durante el test. El hook original y sus 20 entradas
siguen sin alteración.

Este laboratorio incorpora **nuevos scripts** para probar hipótesis sin promocionar
la Suite a 1.4.7. No hay cambios en su manifiesto, identidad, TaskStore, Relay,
Spiral, BAGO-CORE, pytest-checkpoint, política ni codex-profiles.

## Roles y fronteras

1. **SessionStart V1** (fuente congelada): inventario del `cwd` recibido.
2. **Context Lifecycle Lab / SessionStart V2**: descubrimiento ascendente acotado,
   estructura validada y proyección semántica **DATOS NO CONFIABLES**. Solo lectura.
3. **Context Manager Lab**: plan de inicialización de tres documentos + estructura;
   creación solo con aprobación explícita, en raíz marcada y sin sobrescritura.
4. **Actualización propuesta**: se modifica únicamente estado/handoff, preservando
   campos desconocidos, verified_state, checks y las secciones manuales del handoff.
   Todo objetivo nuevo queda `PROPOSED`, nunca `VERIFIED`.
5. **TaskStore 1.4.6**: autoridad local sobre STOP y ledger; `apply-update`
   adquiere `BEGIN IMMEDIATE` y ejecuta `_admit` del TaskStore vigente antes
   de tocar archivos. STOP no se duplica ni se infiere desde Markdown.
6. **Host Codex CLI**: autoridad efectiva para herramientas, permisos y confianza
   en hooks. No se simula como si fuera verificado.

## Flujo operativo sintético

`inspect` → `plan-bootstrap` → rechazo sin aprobación → `apply-bootstrap`
→ descubrimiento anidado → TaskStore.init → TaskStore.stop → rechazo de update
→ inspección STOP → TaskStore.resume explícito → rechazo por snapshot caducado
→ update con revisión vigente → recuperación de objetivo → preservación manual
→ STOP final → reporte con hashes y resultados.

No se crea segundo ledger de permiso. Los informes en carpeta de prueba no son
un registro de autoridad y jamás sustituyen un Receipt de ejecución real.

## Límites reconocidos

- **NO GO de producción:** falta revisión de contrato de host, integración
  con Operating Layer/SessionStart oficial, pruebas Windows reales, aislamiento
  frente a escrituras concurrentes hostiles, privacidad de contexto y regresión
  integral del sistema instalado.
- Un proyecto puede contener texto hostil o desactualizado. Los datos se marcan
  como no confiables; el filtrado de la demo no es un blindaje contra injection.
- Descubrimiento por marcador `.bago/CONTEXT_STRUCTURE.json` significa candidato,
  NO identidad/propiedad/autoridad confirmada.
- Los cambios de estado/handoff son **dos operaciones de reemplazo separadas**:
  bloqueo de STOP en la misma transacción DB, pero fallo parcial filesystem
  requiere reconciliación posterior. NO afirmar atomicidad multiarchivo.
- El `TaskStore` extraído y ejecutado durante la prueba corresponde al propio
  módulo legado; su suite no ejecuta efectos arbitrarios en esta simulación.
- No se ha hecho instalación de hooks ni modificación real de proyectos.

## Criterios de aceptación

- Verificador original BAGO5os 1.4.6 PASS con bytes intactos.
- Demo original de 1.4.6 PASS y nueva batería PASS; las 28 pruebas originales completas
  se ejecutan solamente con `--legacy-full` para diferenciar su coste y resultado.
- Creación controlada de los cuatro archivos exclusivamente en fixture.
- Descubrimiento de raíz desde subcarpeta; límite por repo anidado.
- STOP persistente de TaskStore rechaza la actualización.
- Snapshot SHA invalida autorizaciones obsoletas.
- Proyección semántica no promueve claims a permisos ni evidencias.
- Handoff manual, extensiones y archivos externos permanecen intactos.
- Informe final `REPORT.json`, con límites `NOT_RUN` explícitos.

## Camino a implementación real (no ejecutado)

1. Releer base instalada y comprobar contratos; no copiar scripts sin revisión.
2. Diseñar proyección con privacidad y distinción de contexto/autoridad.
3. Incorporar Context Manager como capacidad invocada desde BAGO-CORE.
4. Mantener SessionStart **solo lectura** y validación real de confianza.
5. Enlazar STOP/Relay sin rutas de ejecución alternativas.
6. Test end-to-end en Windows Codex CLI, pruebas de carrera/TOCTOU y auditoría
   diferencial antes de marcar IMPLEMENTADO y VERIFICADO en plugin.

**Estado:** IMPLEMENTADO EN LAB / TEST SINTÉTICO. No confundir con 1.4.7 instalado.


## RC2 — incidencia de ordenación Path por plataforma

Fuente: REPORT(1).json (Windows, Python 3.14.5). 1.4.6 original rechaza la identidad
antes de comenzar la E2E. Hipótesis reproducida por comparación de PurePosixPath
contra PureWindowsPath: orden de archivos distinto, conjunto/bytes no necesariamente
diferente. RC2 prueba derivado efímero con ordenación POSIX explícita, verifica
manifest y PACKAGE_IDENTITY recalculados. El original sigue inmutable;
no se interpreta un PASS del derivado como aprobación del baseline original.
La distribución instalable, Codex host y transacciones multiarchivo siguen NOT_RUN.
