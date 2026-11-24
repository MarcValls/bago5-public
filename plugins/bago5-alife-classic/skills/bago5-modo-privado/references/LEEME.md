# Modo privado BAGO5 · 0.4.22

## Qué está disponible

Skill de cesión integrada en el plugin, núcleo cooperativo SQLite, lanzador Windows,
UI local Tk y tests. La ruta segura `--check` funciona sin instalar ni abrir KeePassXC.
No hay adaptador real de ChatGPT/Codex/Copilot/ADL: la operación sensible está BLOCKED.

No introducir secretos reales para probar este incremento. KeePassXC y el KDBX siguen
bajo control del usuario; el plugin no instala el gestor ni crea/desbloquea el vault.

## Primera ejecución: batería completa, datos ficticios

Desde raíz del plugin:
`python -B -m unittest discover -s skills/bago5-modo-privado/tests -v`

Necesita Python >=3.11 y Tk para UI. En Linux sin display:
`xvfb-run -a python -B -m unittest discover -s skills/bago5-modo-privado/tests -v`

En Windows se incluye `scripts/01_VERIFICAR.cmd`; no instala Python ni cambia política
PowerShell. Las pruebas usan directorios temporales. Sin display hay tests UI omitidos:
no presentarlos como comprobación visual. No se ejecutan pruebas del resto del runtime.

## Segunda ejecución: comprobar ruta real

`python -B skills/bago5-modo-privado/scripts/private_mode.py --check`

Resultado esperado hoy: `BLOCKED`, `HOST_UNAVAILABLE`, código de salida 3.
No hay `--force`, `--host-safe` ni mecanismo conversacional de desbloqueo.

## Uso mediante BAGO5

Decir «BAGO, guarda una contraseña» o invocar `$bago5-modo-privado` activa el protocolo,
no una promesa de aislamiento. BAGO no pide datos de la entrada. Sin host verificado,
se detiene. Con integración futura validada, abre el gestor y ofrece los controles
locales: He terminado, Cancelar y reanudación explícita con confirmación de seguridad.

## Continuar implementación del host

Leer `HOST_CONTRACT.md` y `HANDOFF.md`. No copiar SyntheticHost a producción. Integrar
la barrera en las rutas reales y comprobar los observadores del host, no crear otra
superficie o servicio para ocultar una integración que falta. El prompt no es un host.

## Distribución

La actualización enviada a Plugin Creator es un OVERLAY aditivo: conserva archivos
omitidos, no borra paths ni cambia audiencia/MCP. El ZIP de código/evidencias no es una
exportación completa de BAGO5 y no debe instalarse como sustituto del plugin entero.
El plugin publicado contiene lo anterior más este incremento. No se ha modificado
`M:\`, Windows, repositorios, Sites, M0 ni plantillas de Memoria Viva.
