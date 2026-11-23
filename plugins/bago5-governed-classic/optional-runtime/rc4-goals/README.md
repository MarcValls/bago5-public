# BAGO5os 1.4.7 — GOALS RC4_STOP_RECOVERY

Derivada aislada de RC3, SHA256 `036a0f925d0dc90ce20934dfe9c3a4631126c57be8af8854aebd5627d7e17796`.
Los 603 archivos originales RC2 y la Suite de 600 archivos conservan sus bytes. Esta capa externa no se instala automaticamente.

## Operacion y autoridad

`GOALS_RESUME.cmd` solo presenta un resumen; no ejecuta ni es `/goal resume` nativo.
`GOALS_DESPACHAR.cmd` pide workspace y consentimiento de lectura, admite una ronda nativa y despacha un turno.
Busca `py -3` y, si el launcher no esta disponible, `python`. `GOALS_VERIFICAR.cmd` ejecuta la bateria local con hijos simulados, no Codex real.

El selector conserva la mision OPEN iniciada y no permite saltar a otra por DONE/PAUSED documental. Solo CLOSED nativo retira la cabecera. Un turno correcto mantiene OPEN y devuelve WAITING_TASKSTORE_EVIDENCE: consumir evidencia y cerrar siguen siendo operaciones separadas y explicitas.
Codex recibe `exec --sandbox read-only --skip-git-repo-check -`, el plan congelado y el documento DATA_ONLY por stdin. El documento no otorga permisos. El sandbox read-only no impone por si solo el alcance semantico exacto del plan.

## Cancelacion independiente y recuperacion

Antes de admitir ronda/hijo se adquiere un bloqueo OS exclusivo por ledger y se crea y sincroniza `.bridge-run.<task>.json`. Si falla la preparacion, no se ejecuta el turno. El propietario conserva el bloqueo hasta terminar la supervision y cualquier escritor de STOP.

STOP normal sigue usando TaskStore. Si escribir STOP falla, un canal de memoria compartida pide cancelar el worker inmediatamente; si la escritura tarda mas de 200ms, se activa el mismo fallback. El worker observa ese canal y termina su Job en Windows. Se asigna a si mismo al Job antes de crear el CLI: los hijos ordinarios CreateProcess pertenecen al Job desde su creacion. No se habilita breakaway. El cierre del worker libera el handle y termina los descendientes restantes. No se afirma control sobre procesos externos creados mediante servicios/WMI ni agentes ajenos.

El intervalo de 200ms es el fallback desde el intento de persistencia, no una cota total desde cualquier STOP. La consulta del grupo es por sondeo y la CLI puede esperar los timeouts SQLite mientras su hijo ya esta cancelado. El IPC no se cierra mientras quede un watcher con acceso. Una salida incierta o cancelada conserva el latch durable aunque falle escribir el marcador adicional de recuperacion.

Si no se pudo persistir STOP, el bridge informa BLOCKED y el ledger puede seguir ACTIVE. No inventa STOPPED: cancelacion del proceso y control persistido son evidencias distintas. El latch impide nuevas admisiones hasta una recuperacion explicita.

`task-resume --goal A --reason "..."` reanuda solo A. Permite hacerlo aunque B continue STOPPED; B sigue bloqueando cualquier despacho. No abre rondas ni ejecuta hijos. Para un latch pendiente, exige binding, workspace y mision correctos, tarea OPEN, ausencia de runs RUNNING y que no haya dispatcher vivo propietario del bloqueo. Si A sigue ACTIVE por fallo previo, primero persiste STOP nativo y despues ejecuta resume nativo. Solo tras el exito elimina los markers de A. Nunca elimina los de B ni reanuda automaticamente.

Si el proceso anterior murio y el ledger conserva RUNNING, esta CLI no inventa su finalizacion: se requiere reconciliar ese estado mediante el contrato nativo del host antes de reanudar.

## Evidencia de esta candidata

La entrega completa es un contenedor con `candidate.zip`, identidad/manifiesto y `evidence/`: recibos de comandos, logs, comprobacion independiente y resultados reales cuando se hayan ejecutado. El SHA final de candidate.zip se registra en esos recibos externos que lo acompanan. No se pretende introducir dentro de un ZIP su propio hash final.

Los archivos `evidencias/`, LEER_PRIMERO_RC3 y docs/HISTORICO_RC2_* heredados son historicos. No acreditan esta candidata. El dictamen vigente es el informe que acompana candidate.zip. Los 17 tests RC2 y 13 tests RC3 se conservan; RC4 agrega regresiones especificas.

Integracion Goal nativa, app-server y SDK: **NOT_CONNECTED**. Windows es la plataforma del ensayo; otras plataformas requieren ejecucion propia y quedan NOT_RUN. No hay daemon, instalacion, fusion, publicacion ni cambios a .codex/hooks/goals reales.

Base tecnica de herencia y terminacion del Job: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
