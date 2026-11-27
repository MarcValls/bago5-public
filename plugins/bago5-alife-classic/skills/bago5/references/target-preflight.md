# Comprobación previa del destino y de sus versiones

Esta regla se aplica antes de elegir o fijar una versión, runtime, dependencia, imagen, configuración, proveedor o arquitectura para un destino, o de preparar, implementar, instalar, publicar o ejecutar una acción cuyo resultado dependa de esos hechos. También se aplica al delegar: el alcance, el destinatario y las pruebas deben incluirla.

En planes por fases, esta comprobación de hechos del destino forma parte del [preflight obligatorio de cada fase](../../bago5-plan-por-fases/references/phase-preflight.md). Un destino compatible no acredita por sí solo herramientas, acceso, autorización ni capacidad de ejecutar, verificar y entregar toda la fase. Aplicar ambos contratos sin repetir consultas que sigan vigentes y cubran el mismo alcance.

## 1. Resolver qué se va a tocar

Identifica el producto o servicio, propietario o ámbito autorizado, proyecto y candidata, acción concreta, destino y entorno exactos (producción, staging, desarrollo o experimento local). Enumera solo los hechos que condicionan esa acción: versión en ejecución, versiones seleccionables, soporte, extensiones y módulos, arquitectura, credenciales/permisos efectivos, base de datos, límites, configuración, estado o cualquier otra capacidad relevante. Diferencia lo **deseado** por el usuario de lo **observado** en el destino.

## 2. Comprobar antes de depender de un dato

Consulta el destino por medios realmente disponibles y autorizados: panel autenticado, API o conector del propio servicio, inspección del proceso o comando sobre el runtime exacto, o una observación actual y explícita del usuario sobre ese destino. Anota hecho, valor, origen o referencia comprobable, fecha/hora, identidad del destino, entorno y alcance. Usa documentación oficial para soporte, compatibilidad y opciones ofrecidas, pero no la confundas con la versión instalada. Un README, recuerdo, captura antigua, informe, plantilla, lockfile o despliegue anterior sirve para localizar y contrastar: por sí solo NO verifica el estado actual.

Un contenedor, emulador o versión de desarrollo demuestra solo ese experimento: no identifica el runtime de hosting. No fijes una versión de destino, ni prepares sus imágenes, dependencias o configuración como baseline basándote en esos indicios. Por ejemplo, una anotación histórica «PHP 7.4» no autoriza preparar el hosting para 7.4 sin comprobar la versión actual o disponible; una prueba local de 7.4 no la comprueba. Tampoco infieras que la versión más reciente anunciada está instalada.

Antes de pedir otra terminal, host o autenticación, aplicar [continuidad operativa](operational-continuity.md): identificar la operación inmediata y comprobar qué canal ya disponible puede cubrirla. Distinguir acceso al panel, ejecución en su consola, API y SSH de cada operador. La ausencia de SSH en el ejecutor actual no demuestra ausencia de acceso al servidor por otra ruta autorizada; la existencia del panel tampoco demuestra que esa ruta permita la operación. Conservar las comprobaciones vigentes y justificar cualquier cambio con la carencia concreta, sin eludir rechazos de permiso.

## 3. Puerta y recuperación

Si falta o contradice un hecho material del destino, marca el hecho `UNVERIFIED` o `CONFLICT`, la acción dependiente `BLOCKED/NOT_RUN` y no ejecutes ni prepares como definitiva esa variante. Busca otra fuente autorizada, continúa el trabajo independiente y pide al usuario únicamente la intervención que realmente falte. Se permiten experimentos aislados explícitos, version-agnostic o multicandidata, marcados `EXPERIMENTAL` y sin presentarlos como destino observado ni despliegue. La autorización para trabajar no convierte una suposición en evidencia, ni exige repetir confirmaciones rutinarias ya otorgadas.

Revalida antes de un efecto cuando cambie el destino, configuración, release, permisos, identidad, entorno o exista indicio de obsolescencia; conserva el alcance y las fuentes anteriores como historia. No introduzcas secretos en recibos. El estado histórico no se borra ni se eleva a actual por repetición.

## 4. Apoyo comprobable, sin fingir una barrera técnica

Cuando haya Python y sea útil, `scripts/target_preflight.py` evalúa un recibo JSON contra este contrato y rechaza datos históricos, destino/entorno distinto, ausencia de fuentes, tiempo obsoleto o incompatibilidad declarada. El programa NO consulta el destino ni certifica que el recibo sea auténtico; tampoco intercepta ni bloquea por sí mismo herramientas, agentes, instalaciones o despliegues. El asistente debe hacer las comprobaciones reales y aplicar la puerta antes de actuar. En hosts sin ejecución, aplicar manualmente los mismos criterios y declarar `NOT_RUN` cualquier comprobación no efectuada.
