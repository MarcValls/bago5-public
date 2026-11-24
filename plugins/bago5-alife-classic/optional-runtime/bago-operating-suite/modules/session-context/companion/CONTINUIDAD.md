# Continuidad · BAGO SessionStart CLI · 0.1.0-RC1

## Objetivo y decisión vigente

Marc usa **Codex CLI**. La mención inicial al escritorio no describe su flujo.
Implementar primero un hook informativo `SessionStart`, de solo lectura, que
comunique el inventario del contexto BAGO. Configuración directa `hooks.json`.
Agrupar skills en plugin, `PreToolUse` y una interfaz/MCP son posibilidades futuras.

Se revisó el ZIP BAGO5os 1.4.5 CONTEXT-BOOTSTRAP y el perfil de trabajo actual
`Instrucciones generales de ChatGPT — Perfil de trabajo.md` (versión consultada 0).
El ZIP contiene 570 entradas. Su bootstrap existente exige raíz confirmada y
revisión completa del contexto antes de inicializar cuando ya existen archivos.
No se modificó el ZIP ni se instaló o editó ninguna skill.

## Decisiones implementadas

- La raíz proviene solo del `cwd` del evento y mantiene estado candidato.
- No se asciende a carpetas superiores ni se reutiliza un proyecto anterior.
- La estructura v1 original se conserva por bytes y por SHA-256.
- El hook no importa ni llama al bootstrap de escritura.
- `additionalContext` contiene inventario, nunca cuerpos de documentos.
- Existencia, identidad de bytes, revisión semántica y permisos son cosas distintas.
- No se genera un segundo ledger, registro de permisos o almacén de contexto.
- No hay instalación, confianza o activación automática de hooks.

## Mapa del paquete

- `hooks/session_start.py`: entrada real stdin/stdout.
- `schemas/project-context-structure.v1.json`: copia canónica sin cambios.
- `scripts/print_cli_config.py`: propuesta de configuración para el host donde se ejecuta.
- `scripts/demo.py` y `DEMO.ps1`: demostración en fixture temporal.
- `tests/`: pruebas de comportamiento y guardia de auditoría Python para efectos prohibidos.
- `evidence/`: baseline, plan, huellas, resultados, log, demo y matriz de host pendiente.
- `README.md`: pasos de uso y comprobación.
- `CONTRATO.md`: límites e invariantes.

## Estado y evidencias

IMPLEMENTADO y VERIFICADO en el proceso Python local/sintético según
`evidence/REPORT.json`. La configuración se ha generado y el comando resultante
se ha ejecutado en Linux; esto no prueba el parser de hooks de Codex.
Codex CLI y PowerShell no están disponibles en el entorno de verificación.
La integración real Windows/CLI permanece **NOT_RUN**. No se declara FROZEN.
La conservación del ZIP acredita identidad de bytes, no reejecución funcional
de las 570 entradas de BAGO5os.

## Siguiente acción concreta

1. En Windows, extraer el paquete en una carpeta estable y ejecutar la demo.
2. Ejecutar `print_cli_config.py` allí y revisar la definición generada.
3. Fusionarla, conservando las entradas existentes, en `.codex/hooks.json`
   del proyecto confirmado. No usar a la vez la copia global para esta prueba.
4. Registrar `codex --version`; iniciar CLI en la raíz, revisar y confiar en
   la definición mediante `/hooks`; reiniciar una sesión para observar `startup`.
5. Completar `evidence/HOST_CHECKS.json` con hechos y referencias reales. Mantener
   `NOT_RUN` o `UNKNOWN` en los recorridos que no puedan observarse.
6. Probar reanudación, fork y compactación según la versión del host, y comparar
   `cwd` con el proyecto correcto. Ensayar subcarpeta para comprobar que no se
   adopta un padre automáticamente. Conservar capturas o salidas del hook.

## Instrucción de arranque para el siguiente agente

Lee README, CONTRATO y REPORT antes de actuar. Continúa BAGO-SCR-001 en Codex CLI.
Mantén el hook de solo lectura y no amplíes el alcance a init, PreToolUse o MCP.
Inspecciona la configuración existente del proyecto y prepara una fusión revisable;
no reemplaces otras definiciones ni confianza. La confianza debe concederla Marc
en el host. Verifica el evento real y cwd; si no hay evidencia de ejecución,
no marques la integración como verificada. Conserva el ZIP BAGO5os original y los
contratos de revisión del bootstrap. Entrega resultados ligados al candidato.

## Riesgos y límites restantes

El `commandWindows` se genera para rutas ordinarias y un lanzador Python disponible;
se rechazan caracteres que podrían interpolarse en shells. Ese comando requiere
ejecución real en Windows. Las comprobaciones de symlink en Linux no certifican
junctions de Windows ni aislamiento frente a carreras de directorios.
Los fallos del hook no impiden que Codex use otras herramientas: este prototipo
informa del contexto, no gobierna todas las acciones del agente.
