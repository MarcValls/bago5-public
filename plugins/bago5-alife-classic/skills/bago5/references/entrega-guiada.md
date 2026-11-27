# Entrega guiada de procesos repetibles

## Alcance y autoridad

Preferencia expresa de Marc: en entregas de procesos deterministas o repetibles con scripts y paquetes, numerar pasos, comenzar con una batería completa e indicar el siguiente paso. Aplicar a cada proyecto sin imponer una arquitectura o copiar scripts de otro proyecto. Los ejemplos no son comandos universales. Respetar instrucciones actuales, restricciones, autorización, plataforma y STOP. Una consulta, explicación simple o actuación de una sola operación no obliga a crear archivos; no convertir en determinista una salida de modelo, un servicio externo o un proceso concurrente por ponerle un lanzador.

Identificar entrada, precondiciones, estado, efectos, aceptación, dependencias y resultado. Diferenciar la parte determinista, sus condiciones y las partes inciertas. Un mismo input solo produce el mismo output si el entorno y las dependencias pertinentes son equivalentes; declarar semillas, versiones y límites cuando importen. Reutilizar herramientas y procesos existentes. No inventar scripts, dependencias o efectos realizados.

## Secuencia guiada

Cuando proceda una entrega con varios scripts, usar prefijos numéricos correlativos y nombres claros. En Windows, si el stack lo permite, proporcionar lanzadores `.cmd` de doble clic que invoquen `.ps1` junto a ellos; respetar otras plataformas y las instrucciones expresas. No fijar rutas de usuario: resolver recursos relativos al propio paquete y citar cualquier dependencia externa. Preservar ejecutables y convenciones existentes cuando renombrarlos rompa compatibilidad; añadir una ruta guiada compatible cuando sea posible.

1. **Primera ejecución — batería completa**: `01_BATERIA_COMPLETA` o equivalente específico. Inventariar y ejecutar todas las comprobaciones pertinentes que puedan hacerse en esa fase: integridad, dependencias, configuración, compatibilidad y pruebas preinstalación. Una batería completa incluye las comprobaciones posteriores como NOT_RUN si requieren una fase aún no realizada, con motivo y siguiente acción; no ejecutar instalaciones, cambios de datos, publicaciones o acciones externas solo por existir en la secuencia. No proclamar resultado global PASS si hay fallos o comprobaciones obligatorias NOT_RUN; usar un resultado agregado con límites, o no darlo.
2. **Instalación o preparación**, si existe y está autorizada: paso numerado siguiente. Explicar destino y efectos, conservar datos, no sobreescribir ni eliminar lo anterior sin permiso y verificar que el paso terminó realmente. Si no hay instalación necesaria, omitir este paso y mantener la numeración consecutiva.
3. **Verificación posterior**, cuando corresponda: volver a intentar las pruebas antes imposibles y revisar funcionalidad y regresiones pertinentes. Diferenciar integridad, ejecución, comprobación, simulación y verificación real en la plataforma. Evitar pruebas destructivas por defecto. Si la prueba exige acceso u operación no autorizada, marcar NOT_RUN con motivo.
4. **Inicio u operación**, si corresponde: lanzar la función solicitada y mostrar el estado real. Una salida de script, configuración o hash no demuestra por sí sola que una aplicación, plugin o servicio esté funcionando.

Adaptar los nombres, número de pasos y sus dependencias. No ejecutar automáticamente la fase siguiente: cada paso comunica al terminar resultado, evidencias relevantes y **qué archivo o acción sigue**. Ante FAIL, requisito ausente, STOP o condición insegura, no orientar a continuar como si todo hubiera pasado: indicar diagnóstico, reparación o requisito pendiente. Un paso no ejecutado es NOT_RUN, no fallo ni éxito. Cuando una fase no sea necesaria explicarlo y evitar pasos vacíos.

## Entrega y comprobación

Proporcionar instrucciones breves LEEME para descomprimir, requisitos, primer paso, secuencia, resultados, ubicación de evidencias y resolución de errores. En ZIP incluir SHA256SUMS, comprobar rutas relativas y archivo íntegro; los hashes solo acreditan integridad respecto a la lista, no autoría, actualidad ni funcionamiento. No entregar ZIP sin instrucciones. Cada script debe comunicar el efecto que realiza, mantener la ventana visible cuando se use por doble clic y devolver un código de salida coherente donde el host lo permita. Los lanzadores `.cmd` deben transmitir el código de salida del proceso, incluso tras `pause`.

Antes de entregar: comprobar la secuencia efectiva, nombres y referencias; probar pasos positivos y negativos pertinentes y que la batería no produzca efectos no autorizados. Para Windows probar PowerShell/CMD en Windows o marcarlo NOT_RUN; no afirmar compatibilidad únicamente por inspección. Verificar qué pasa con prerequisitos ausentes, códigos de error, rutas con espacios y ejecución repetida cuando importen. Si no hay host o permisos, conservar evidencia de lo comprobado y dar NOT_RUN para lo demás. No afirmar que un asistente ejecutará automáticamente pruebas por recibir un prompt.

Usar los [vectores de aceptación](entrega-guiada-vectores.json) como casos a ejecutar y adaptar al proyecto. Son especificaciones, no resultados ni garantía de una batería automatizada.
