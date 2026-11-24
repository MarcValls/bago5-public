# Relevos cooperativos de agentes — BAGO5os 1.4.5 RELAY-RC1

## Qué incorpora

`task collaborate` amplía el controlador existente `suite_control.py` y su base
`control.sqlite3`. No añade un segundo orquestador ni sustituye pytest.

Conserva el candidato y su alcance, la identidad de la Suite, el contexto
explícito, las decisiones, el trabajo pendiente y las evidencias. El sucesor
acepta el digest exacto del relevo. La aceptación comprueba de nuevo archivos,
recibos y candidato, y entrega una credencial de coordinación nueva; la anterior
ya no permite continuar. No transfiere memoria interna del modelo ni permisos.

**Modalidad inicial: COOPERATIVE_SERIAL.** Diferentes agentes se relevan, pero
no trabajan simultáneamente. La misión puede continuar entre procesos y sesiones
hasta sus presupuestos explícitos. No se promete duración ilimitada.

## Demostración independiente desde el paquete instalado

```powershell
python -B C:\BAGO5os-lab\1.4.5\scripts\suite_orchestrator.py task collaborate demo --output C:\BAGO5os-lab\relay-demo-01
```

La carpeta de salida debe ser nueva y estar fuera de la instalación. Tres procesos
Python deterministas actúan como trabajadores A, B y C: A registra contexto y
ofrece el relevo; B acepta y materializa el resultado; C comprueba el resultado
con otro programa y otro rol. Se rechazan una credencial obsoleta y una evidencia
alterada. Se producen `DEMONSTRATION.json`, el ledger, checkpoints, recibos y logs.

**No son tres agentes LLM.** La demo prueba procesos, protocolo e integración con
la CLI. No acredita conexión operativa a Codex, Copilot, ADL o un proveedor.
Windows/PowerShell es un ejemplo de uso, no una plataforma verificada aquí.

## Crear una misión

Los ejemplos de [plan](examples/plan.json), [configuración](examples/config.json)
y [contexto](examples/context.json) son plantillas revisables. Los archivos
`candidate.txt`, `work_check.py` y `verify_check.py` del plan deben existir en el
workspace elegido antes de iniciar; sustituye los nombres por tus archivos reales.
No ejecutes código de fuentes desconocidas por aparecer en una plantilla.

```powershell
$S = 'C:\BAGO5os-lab\1.4.5\scripts\suite_orchestrator.py'
$State = 'C:\BAGO5os-lab\misiones\mision-01'
python -B $S task init --state-dir $State --workspace 'C:\Proyecto' --plan .\plan.json
python -B $S task collaborate enable --state-dir $State --config .\config.json
python -B $S task round --state-dir $State
python -B $S task collaborate guide --state-dir $State
```

El directorio de estado debe ser nuevo y estar separado del workspace. `enable`
solo se admite una vez, antes de abrir rondas. La configuración fija trabajadores,
roles, verificaciones y presupuestos; no se amplían silenciosamente después.

## Trabajador A: reclamar y entregar

```powershell
$lease = python -B $S task collaborate claim --state-dir $State --check work --worker agent-A | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'No se pudo reclamar el trabajo' }
$env:BAGO_RELAY_TOKEN = $lease.lease_token
python -B $S task collaborate checkpoint --state-dir $State --check work --worker agent-A --context .\context.json
$offer = python -B $S task collaborate offer --state-dir $State --check work --worker agent-A --to-worker agent-B --context .\context.json --reason 'Límite de contexto próximo' | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'No se pudo registrar el relevo' }
Remove-Item Env:BAGO_RELAY_TOKEN
$offer | ConvertTo-Json -Depth 100 | Set-Content -Encoding utf8 .\relevo.json
```

No guardar el token del claim dentro del relevo. `offer` revoca la credencial
anterior antes de que el sucesor pueda continuar. El host entrega `relevo.json`
al agente real; esta CLI no lo crea ni lo activa.

## Trabajador B: aceptar, ejecutar y registrar

```powershell
$offer = Get-Content .\relevo.json -Raw | ConvertFrom-Json
$lease = python -B $S task collaborate accept --state-dir $State --handoff $offer.handoff_id --worker agent-B --ack-sha256 $offer.sha256 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Relevo rechazado; no continuar' }
$env:BAGO_RELAY_TOKEN = $lease.lease_token
python -B $S task run-check --state-dir $State --check work --worker agent-B --timeout 60 -- python -B work_check.py
if ($LASTEXITCODE -ne 0) { throw 'Conservar el fallo; no cerrar la comprobación' }
python -B $S task consume --state-dir $State --check work --worker agent-B
python -B $S task collaborate finish --state-dir $State --check work --worker agent-B
Remove-Item Env:BAGO_RELAY_TOKEN
python -B $S task collaborate guide --state-dir $State
```

El verificador `agent-C-verifier` reclama `verify` y ejecuta/consume/finaliza su
propio check. El rol ejecutor no puede reclamar esa verificación. La independencia
es de rol/proceso lógico: no prueba que el evaluador esté diseñado por otra persona.
Finalmente `task close --state-dir ...` revalida la evidencia completa; finalizar
un relevo no equivale a validar el producto.

## Interrupción, relevo y recuperación

`heartbeat` renueva una credencial aún válida. No revive una caducada. Antes de
lanzar una comprobación, la vigencia restante debe superar su timeout más un
segundo. `run-check` supervisa su proceso y retira `BAGO_RELAY_TOKEN` del entorno
del hijo. No se debe entregar el token a las pruebas.

`task stop --reason ...` es persistente y revoca todas las credenciales activas.
`task resume --reason ...` no las revive. Después de detener realmente al agente
anterior y reconciliar sus posibles efectos, el operador puede usar:

```powershell
python -B $S task collaborate recover --state-dir $State --check work --reason 'Host confirmó la salida del trabajador anterior' --confirm-prior-stopped
```

Esa confirmación queda registrada como declaración del operador, no como una
observación del proceso externo. No hay takeover automático ni garantía de que
los efectos externos ocurran una sola vez. Una ejecución registrada como RUNNING
bloquea la recuperación hasta resolver su estado real; no se falsea su recibo.

Para reintentar un check fallido, el trabajador registra su contexto actual con
`release --context ... --reason ...`; después se abre otra ronda y se reclama el
trabajo. Los recibos anteriores se conservan. Se respetan los límites del plan
(1–100 rondas) y de la configuración (claims, relevos y checkpoints).

## Conexión con pytest

Los comandos `pytest-checkpoint doctor/run/resume/status/demo` siguen disponibles
sin cambios. Un check de misión puede ejecutar la CLI del acompañante a través
de `task run-check`. Declara también sus resultados como artefactos cuando sean
criterios de aceptación; no los sustituyas por una frase en `completed`.

El checkpoint de pytest guarda resultados de tests. El checkpoint de relevo
conserva continuidad del trabajo. Son estados distintos y ambos deben corresponder
al candidato efectivo. No copies una base SQLite mientras su escritor sigue activo.

## Límites y fuentes técnicas

No se implementan todavía detección automática del límite de contexto, creación
de agentes del host, colaboración paralela, scheduler permanente ni migración
entre candidatos de código. El controlador existente verifica candidatos
congelados: una reparación de fuente crea un candidato y una misión nuevos.

Los hashes son integridad local sin firma, no autenticación del emisor. Las
comprobaciones del filesystem no son un snapshot atómico ni un sandbox de SO.
La transición de estado y el checkpoint se confirman en la misma transacción
SQLite; una acción externa no participa en esa transacción.

Referencias primarias: [transacciones SQLite](https://www.sqlite.org/lang_transaction.html),
[atomicidad y sus supuestos](https://www.sqlite.org/atomiccommit.html),
[supervisión de procesos Python](https://docs.python.org/3/library/subprocess.html).
