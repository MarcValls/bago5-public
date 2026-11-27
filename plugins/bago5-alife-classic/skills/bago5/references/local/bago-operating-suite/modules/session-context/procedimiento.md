# BAGO5os · SessionStart / contexto revisable

## Activación y responsabilidad

El router de BAGO5os ofrece `session-context doctor`, `session-context config` y
`session-context demo`. La configuración imprimida es una **propuesta**, no una
instalación de hooks ni autorización. El usuario debe integrar manualmente el
bloque `SessionStart` en una única fuente `.codex/hooks.json` y revisarlo en
`/hooks` de Codex CLI. No activar automáticamente hooks globales.

El hook **solo inventaría** los tres artefactos `PROJECT_CONTEXT.md`,
`PROJECT_STATE.json` y `ACTIVE_HANDOFF.md` en el `cwd` del evento de host.
No consume contenido como instrucciones, no reconoce una raíz mediante ascenso,
no importa módulos del proyecto ni ejecuta comandos; informa estados, tamaño y
SHA-256. El marcador `.git` no es autorización de lectura adicional.

El inventario no es una confirmación de identidad del proyecto. Codex debe
confirmar autoridad/alcance con sus mecanismos existentes; antes de ejecutar,
usar el controlador `task`, las políticas y permisos del host. El hook jamás
vincula un permiso de trabajo ni implica reanudación tras `STOP`.

El resultado es apto para informar al operador de qué contexto falta o exige
revisión, y puede acompañar `task collaborate` como pista de continuidad,
**sin fusionar sus almacenes** ni aceptar un handoff automáticamente.

## Herramientas incluidas

El prototipo fuente se conserva sin editar bajo [companion](companion/README.md).
Contrato fuente [BAGO-SCR-001](companion/CONTRATO.md), pruebas
unittest (motor local independiente), demo
synthetic (motor local independiente).

```powershell
python -B scripts/suite_orchestrator.py session-context doctor
python -B scripts/suite_orchestrator.py session-context config
python -B scripts/suite_orchestrator.py session-context demo
```

## Bloqueos / límites

- Codex real, compatibilidad Windows/PowerShell y recepción de eventos: NOT_RUN.
- `PreToolUse`, instalación automática y barrera de escritura: NO IMPLEMENTADOS.
- El hook falla sin detener la sesión: no sustituye a un boundary de autorización.
- Cambiar el script o su ruta requiere nueva revisión de confianza en `/hooks`.
- Los datos del proyecto pueden no ser fiables y NO deben promoverse a canon.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
