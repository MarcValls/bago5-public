# Identidad de versión en cada invocación de `$bago5`

Comenzar toda respuesta gestionada por `$bago5` con `BAGO5 (vX.Y.Z)` y usar la
versión de **la habilidad o distribución cargada en esta invocación**. Una
publicación nueva no demuestra que una sesión anterior la haya cargado.

## Comprobar la fuente cargada

1. Usar metadatos fiables del host que identifiquen el paquete efectivamente
   cargado. Con archivos locales, comprobar que la ruta corresponde a ese
   paquete y ejecutar `python <plugin-root>/scripts/bago5_version.py --json`.
   El script inspecciona su propia distribución por defecto; `--root` permite
   auditar otra copia, sin convertirla en la copia activa.
2. Distinguir identidad primaria de coherencia de etiquetas. Los dos manifiestos
   `plugin.json` y `.codex-plugin/plugin.json` acreditan la versión de esa
   distribución cuando son objetos válidos, identifican `bago5-governed-classic`
   y declaran la misma versión SemVer válida. La cabecera de la habilidad,
   las interfaces, el catálogo y las rutas son superficies derivadas. Si alguna
   discrepa, falta o es inválida, conservar la versión primaria conocida en
   `BAGO5 (vX.Y.Z)` y señalar el defecto por separado, con `DESFASE` cuando
   corresponda. El comprobador conserva `package_version` y devuelve `FAIL`;
   conocer la versión no convierte una distribución incoherente en `PASS`.
3. En Work u otro host sin archivos locales, usar metadatos fiables que
   identifiquen la versión efectivamente cargada. La cabecera del `SKILL.md`
   servido permite contrastar esa identificación, pero por sí sola no es una
   fuente primaria. No exigir una API de identidad de proceso que el host no
   tenga ni atribuir esta versión a un motor local o remoto independiente.
4. Si falta evidencia primaria suficiente o las fuentes primarias se
   contradicen, mostrar `BAGO5 (versión NO_COMPROBADA)` y explicar la causa y las
   versiones observadas. Si no se recupera ninguna fuente cargada, declarar la
   fuente `NO_RECUPERADA`. No escoger la más reciente ni deducirla de memoria,
   conversaciones, ejemplos, títulos de interfaz o una descarga no activada.

La salida del script prueba la coherencia de la **distribución inspeccionada**;
`active_host_release_verified=false` expresa que no inspecciona otros procesos.
Puede usarse como evidencia del paquete cargado cuando el host ha identificado
esa misma ruta. Ante un desfase, bloquear solo las operaciones que dependan de
la identidad o compatibilidad cuestionada y continuar lo independiente.

## Preparar cada release

`plugin.json.version` es la fuente única para las etiquetas de la próxima
release. En una actualización autorizada, cambiar esa versión y ejecutar
`python <plugin-root>/scripts/bago5_version.py --sync --json`. La opción `--sync`
escribe únicamente las superficies vigentes: versión del manifiesto Codex,
etiquetas de interfaz del plugin, etiqueta de la habilidad, cabecera de
`SKILL.md`, versión/etiquetas de entrada del catálogo y `ROUTES.plugin_version`.
Conserva instrucciones,
conexiones, nombres de habilidades, alias y referencias históricas.

Antes de empaquetar o publicar, incrementar explícitamente la versión y ejecutar
la comprobación **sin `--sync`** y las pruebas de identidad. No depender de un
incremento automático del host: puede cambiar solo los manifiestos y dejar
desfasadas las superficies derivadas. Tras publicar, recuperar y comprobar las
fuentes guardadas. No publicar con resultado `FAIL`. La comprobación cubre
los dos manifiestos, la interfaz del plugin, la interfaz de `$bago5`, su
cabecera, las tres superficies del catálogo y la versión vigente del registro
de rutas; también cubre la interfaz
portable si está declarada. Los campos ausentes, malformados o desfasados
fallan explícitamente. Un cambio de etiqueta no ejecuta ni actualiza motores.

La sincronización valida todas las fuentes antes de escribir y sustituye cada
archivo de forma atómica, pero una interrupción entre archivos puede dejar un
desfase detectable. No usarla mientras otro proceso edita esos mismos archivos.
La comprobación ordinaria es de solo lectura y no corrige silenciosamente
fuentes durante una misión.

Esta regla es una instrucción de la habilidad y un control comprobable del
paquete; no es un interceptor universal del host. Informar por separado las
pruebas del paquete, la publicación y cualquier comportamiento probado en el
host. No declarar probado un host por publicar el paquete.

## Agente genérico

La plantilla virtual `bago5-generic` del runtime opcional puede duplicarse y
recibir referencias del catálogo publicado. La clonación crea configuraciones;
`enabled=false` y `skills=[]` son los valores iniciales. El host sigue siendo
responsable de autorizar y ejecutar acciones. Usar el contrato
[Agente genérico clonable](AGENTE_GENERICO_CLONABLE.md).
