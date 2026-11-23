# BAGO-PRIVATE-001 v1 · Contrato de integración y frontera

## Capacidad y aceptación

Proyecto: BAGO5 Classic.
Objetivo: cesión sensible sin entregar secretos al modelo ni a herramientas controladas.
Baseline publicada: 0.4.20 / referencia-de-origen.
Candidata: 0.4.22, mismo ID, audiencia y bindings. No hay instalación del host local.

El componente reutiliza SQLite, exclusión transaccional, subprocess sin shell, Tk y
validación Authenticode; no añade un password manager ni un servicio residente.
El requisito no cubierto en el material recuperado es una barrera vinculante en el
planificador/dispatcher real. Se implementa el gate reutilizable y se deja explícita
esa integración pendiente. El runtime histórico opcional NO es evidencia de host.

## Host confiable, no configuración conversacional

`HostBoundary` es una interfaz Python implementada dentro del host. NO se carga por
una ruta indicada por el modelo y NO se suministra como JSON/certificado autoemitido.
No se incluye adaptador real ni registry que pretenda haberlo instalado. `MissingHost`
siempre niega acceso. Los adaptadores de tests son ficticios y no distribuibles como
prueba de cobertura. No exportar a MCP `Gate.bootstrap`, `transition`, `finish`, pins
ni `WindowsKeePassXC.open`. Solo el dispatcher y UI humana pueden invocarlos.

Antes de integrar, recuperar fuentes exactas, versión y entrada del host activo.
Usar su mecanismo existente de control si existe; no conectar por nombre módulos
históricos. Resolver toda vía fuera de la barrera antes de usar secretos.

`validate_coverage(gate)` debe comprobar cobertura real: inventario de observadores,
procesos/agentes/sesiones controlados; rutas de herramientas, shell/PowerShell, vídeo,
accesibilidad, pulsaciones, portapapeles, lectores de archivos/vault/memoria de proceso,
logs/exportadores, reintentos, workers y permisos. Desconocido => negar.
`freeze_and_flush(gate)` detiene productores/streams, impide nuevos workers, cancela
tareas activas, descarta buffers y neutraliza entregas pendientes. Debe devolver en
un plazo acotado por el host o fallar cerrado. El núcleo espera además active=0.
`confirm_sealed(gate)` comprueba de nuevo cobertura y ausencia de bypass. El recibo
no acredita la afirmación si el host solo devuelve true sin control efectivo.
`prepare_resume(gate)` prepara admisión de NUEVAS solicitudes, sin arrancar antiguos
observadores ni ejecutar colas/reintentos. El gate se abre al final.

Todos los procesos cooperativos usan la MISMA base SQLite local y `Gate.ticket()`
durante TODO el ciclo: adquisición, espera, cómputo, entrega y telemetría. Los streams
mantienen ticket hasta cerrarse realmente. Un callback no puede desasociar un proceso
y liberar su ticket mientras siga observando. Una nueva generación invalida resultados
pendientes. Cerrar admisión antes de drenar evita la carrera check-then-launch.

SQLite y Python no son sandbox frente a código arbitrario del mismo usuario. La ruta
del estado y pins debe tener ACL revisada; el host debe impedir su manipulación y el
acceso directo de modelos a procesos/archivos fuera del dispatcher. La falta de esa
mediación hace BLOCKED la capacidad global, aunque el gate local pase tests.

## Estados y fallos

NORMAL -> PREPARING -> PRIVATE -> RESUMING -> NORMAL.
PREPARING/PRIVATE/RESUMING -> CANCELLED o BLOCKED, siempre con admisión cerrada.
CANCELLED/BLOCKED -> RESUMING solo mediante UI humana y comprobaciones renovadas.
Estado inicial desconocido/nuevo = BLOCKED. Bootstrap es de instalación humana del
host, una sola vez; no equivale a recuperación tras fallo. Un ticket huérfano no caduca
ni se elimina automáticamente: se debe demostrar que el productor realmente cesó.

Cancelar o cerrar no equivale a reanudar. La UI informa del bloqueo persistente.
`He terminado` expresa solo finalización de usuario; `save_verified` es siempre false.
No inferir guardado por código de salida, ventana, vault, accesibilidad o capturas.
Al reiniciar la UI, se exige reconciliación del host y nuevo consentimiento; no se
presume muerto un controlador por antigüedad. Recuperación de huérfanos no implementada
como botón automático; se bloquea hasta disponer de verificación fiable del host.

## Lanzador y procedencia

GUI Windows únicamente: ejecutable absoluto KeePassXC.exe bajo Program Files,
sin UNC/enlaces/junctions, hash SHA-256 local acreditado y firma Authenticode válida
con huella de firmante fijada por el operador. No descargar ni instalar automáticamente.
Los pins no se obtienen del LLM. No usar un hash de procedencia desconocida como prueba
de autenticidad. Revalidar antes del spawn. La firma del instalador por sí sola no
valida cualquier exe; si esa distribución carece de firma compatible, el lanzador
bloquea y se requiere un adaptador de procedencia auditado, no omitir la comprobación.

No argv de vault/clave/cuenta; stdin/stdout/stderr a DEVNULL, shell=False, entorno
mínimo sin variables de secretos ni hooks Qt/Python heredados. El host debe validar
ACLs y los binarios/entorno Windows. Un atacante con escritura en instalación, DLLs,
configuración o privilegios de administrador queda fuera de la garantía.

## Registros y privacidad

SQLite `audit`: únicamente `at` y `state`. `control` y `active` almacenan estado,
generación, identificador aleatorio de controlador y tickets; no nombres de herramientas,
usuarios, cuentas o servicios. No exportar estos controles como credenciales. Errores
solo de enum, nunca traceback/payload ajeno. No retener capturas ni claves de prueba
fuera de los fixtures. No registrar operaciones sensibles en Memoria Viva.

## Verificación del host aún NOT_RUN

Acreditar bloqueo de cada canal REAL, otra sesión/worker, captura ya activa y stream
bufferizado; cierre/fallo/reinicio reales; observación que no cesa; instalación KeePassXC
confiable; lanzamiento y retorno humanos; inspección independiente de logs/argv/entorno
con claves FICTICIAS. Repetir con vault inexistente y KeePassXC ya abierto sin inspeccionar
sus ventanas. Verificar que no se reactiva ningún productor antiguo al volver a NORMAL.
Sin ese recorrido, NO_GO con secretos reales.
