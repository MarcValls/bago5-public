---
name: bago5-modo-privado
description: "Gestiona operaciones con credenciales sin recibir secretos; exige protección técnica comprobada del entorno."
---

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../bago5-ganchos-sesion/SKILL.md) y su [contrato de continuidad](../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](../bago5/references/target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

# BAGO5 · Modo privado / KeePassXC

## Prioridad y alcance

Aplicar ANTES del ciclo de memoria, de una captura, de la automatización o de pedir
campos cuando la intención sea operar con contraseñas. Esta skill no sustituye la
autoridad del host. Conserva STOP, permisos por operación y separación de proyectos.
No pedir servicio, cuenta, usuario, contraseña, clave maestra ni ruta KDBX en el chat.
No guardar esos datos, ni siquiera en Memoria Viva, trazas o instrucciones para agentes.
No reproducir un secreto si el usuario lo pega por error; la entrada ya enviada no
puede hacerse retroactivamente invisible ni prometerse borrada por este plugin.

## Cliente local con entrada enmascarada ≠ sesión PRIVATE

Para la autenticación de un servicio por un cliente local de confianza,
seguir [BAGO5-CRED-001](../bago5/references/entrada-credenciales-locales.md):
preferir un diálogo nativo (usuario y contraseña oculta), o un TTY sin eco
cuando el diálogo no exista. El secreto debe permanecer dentro del cliente
que lo usa; nunca se envía al modelo, un subagente, argumentos, logs o memoria.
Esta ruta no concede ni simula `PRIVATE` ni el modo privado, y no sustituye la barrera del host
cuando haya observadores que deban suspenderse o se manipule un vault/KDBX.
Si no se dispone de un cliente interactivo confiable en el host elegido,
`BLOCKED_LOCAL_INPUT` solo para ese tramo. La imposibilidad de abrir un
KeePassXC privado sigue siendo `BLOCKED · HOST_UNAVAILABLE` como ya estaba.
No instalar ni abrir un gestor, ni pedir credenciales para demostrar la ruta.

## Estado efectivo de esta versión

Implementados: reglas de cesión; gate cooperativo SQLite multiproceso; coordinador;
lanzador Windows con validación de ejecutable; diálogo local Tk de estados y botones;
pruebas sintéticas positivas/negativas y UI ejecutada en Linux/Xvfb.

**Adaptador real de ChatGPT/Codex/Copilot/ADL: NO IMPLEMENTADO.**
No existe un hook instalado que suspenda todas sus herramientas desde esta skill.
La edición del plugin no instala KeePassXC, un MCP local, un daemon ni permisos OS.
Las pruebas de `SyntheticHost` NO acreditan aislamiento en el host del usuario.
El runtime BAGO 4.11.10 opcional del plugin no se ha convertido en host activo.

## Ruta de uso

Invocación directa: `$bago5-modo-privado`. La descripción admite intención natural;
la entrada BAGO5 remite mediante su default_prompt/agents al especialista.
No se inventa un comando CLI `/private` ni un alias en ROUTES.json.

1. Resolver host y alcance **sin observar la interfaz sensible**. No consultar memoria
   de cuentas ni el contenido de un vault para averiguar qué quiere guardar el usuario.
2. Exigir evidencia vigente del adaptador de ese host: todas las sesiones/observadores
   controlados pasan por una misma barrera; no hay bypass por shell, agentes, reintentos,
   archivos, telemetría ni exportadores. Un booleano, hash, habilidad o nombre de clase
   no constituye esta evidencia. Consultar `references/HOST_CONTRACT.md`.
3. Sin adaptador real validado: responder `BLOCKED · HOST_UNAVAILABLE`, explicar que
   no puede confirmarse la suspensión de observación, no abrir el gestor ni simular
   PRIVATE. Se puede indicar el uso manual de KeePassXC fuera de la interacción
   observada, pero no declararlo protegido por BAGO ni verificarlo con capturas.
4. Con un host realmente integrado y autorizado: cerrar admisión primero, detener
   productores y descartar buffers, esperar actividad cero, comprobar cobertura y
   ejecutable confiable. Solo entonces entrar en PRIVATE y abrir la GUI sin argumentos.
5. En PRIVATE, no invocar herramientas, agentes, capturas, vídeo, accesibilidad,
   portapapeles, teclado, archivos temporales, memoria de proceso, KDBX ni servicios
   remotos. Tampoco leer identidad/memoria o hacer verificaciones visuales de progreso.
   La UI local, no un observador del modelo, gestiona el retorno.
6. `He terminado`: exige acción humana local y confirmación de haber bloqueado/cerrado
   el gestor y tratado el portapapeles, si se utilizó. Significa interacción terminada;
   **nunca** «contraseña guardada/verificada». BAGO no comprueba el vault.
7. `Cancelar`, cierre o STOP conservan el bloqueo. Reanudar exige otra acción humana
   explícita. Un reinicio no libera el gate. Una sesión huérfana requiere reconciliación
   del host; no borrar el estado, aplicar TTL o `bootstrap` para sortearla.

## Disponibilidad y datos

El lanzador no instala ni sustituye KeePassXC. Ausente/no verificado => BLOCKED.
No inspeccionar si un vault ya está abierto; avisar que la aplicación podría estarlo.
No admitir argumentos `--pw-stdin`, `--keyfile`, `--allow-screencapture`, rutas KDBX,
CLI de entradas, contraseñas, campos o variables secretas. La operación requiere solo
el ejecutable previamente acreditado por el operador. Sin firma/pins confiables,
instalación protegida y permisos verificados, no lanzar. Una firma MSI no demuestra
que cualquier exe colocado en la misma carpeta sea auténtico.

KeePassXC sigue siendo dueño de la UI y el usuario del archivo KDBX. No hay acceso
al contenido por BAGO. La protección no abarca procesos ajenos, malware, Windows
comprometido, administradores, dispositivos de captura ni historiales del portapapeles.

## Ejecución de comprobaciones

Desde la raíz real del plugin y con Python >=3.11:

`python -B skills/bago5-modo-privado/scripts/private_mode.py --check`

El resultado actual es BLOCKED/HOST_UNAVAILABLE, exit code 3, sin escrituras ni
apertura de aplicaciones. Es el comportamiento seguro esperado, no una integración.

`python -B -m unittest discover -s skills/bago5-modo-privado/tests -v`

Las pruebas usan datos ficticios y directorios temporales. No lanzar pruebas sobre
claves reales ni utilizar el adaptador sintético fuera del directorio de pruebas.
UI requiere Tk y display; si faltan, NOT_RUN, no PASS visual. Ver `references/LEEME.md`.

## Cierre

Aplicar la [decisión de turno](../bago5/references/turn-decision.md#sustentar-el-cierre-y-retomar-el-encargo) sin debilitar esta frontera. HOST_UNAVAILABLE bloquea la operación sensible y sus dependientes por falta del adaptador real validado: explicar esta regla y [su fuente](references/HOST_CONTRACT.md), con la mínima intervención necesaria. No es preciso intentar observar o manipular secretos para demostrar el bloqueo. NOT_RUN/NO_COMPROBADO describen el estado; no sustituyen esa razón.

Solo puede continuar trabajo independiente que no exponga secretos cuando no esté activo PRIVATE, un gate cerrado o STOP. La intervención humana no verifica el guardado ni abre por sí sola el gate: conservar el retorno local y la reconciliación exigidos arriba. Tras una salida realmente autorizada, retomar el encargo y comprobar únicamente resultados no sensibles por canales permitidos, sin repetir permisos vigentes ni leer el vault. En Work este procedimiento lo aplica el agente; los ganchos de sesión no suplen el adaptador privado NO IMPLEMENTADO.

Diferenciar implementación del componente, tests, publicación del plugin y validación
Windows/host. No afirmar privacidad operativa hasta completar la batería del host.
Logs: solo tiempos/estados; no entradas, cuentas, campos, rutas de vault o capturas.
Mantener NORMAL como estado adicional para representar reanudación sin ambigüedad.
