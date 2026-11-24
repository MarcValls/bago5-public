# Marketplace ALIFE · cliente de BAGO5

Reutilizar el registro canónico `https://alifememories.com/api/templates` y su
consulta `/api/templates/compatibility`. No crear otro catálogo de releases ni
confundir el catálogo de habilidades del plugin con el servicio remoto.

## Configuración y anfitriones

El instalador Windows conserva el marketplace nativo de Codex y sus otras entradas.
Añade una preferencia independiente `bago5.alife-marketplace.v1` bajo
`.agents/plugins/bago5/alife-marketplace.json`, con endpoints públicos y sin credenciales.
La configuración es idempotente; una diferencia produce conflicto y conserva el archivo,
sin reemplazar otro destino. Registrar direcciones no acredita acceso remoto.

En ChatGPT/Work utilizar las herramientas ALIFE reales de listar/recuperar plantillas y
comprobar compatibilidad si están expuestas. Sus nombres pueden llevar prefijo del conector.
Sin herramienta, leer los endpoints públicos mediante una capacidad autorizada. No
solicitar ni transportar tokens para un catálogo público. Con ejecución local, utilizar
`scripts/alife_marketplace.py`; no instalar el ayudante por invocar una skill.

## Resolver un release

1. Consultar el catálogo y conservar `template_id`, `version`, `status`, `manifest`,
   `package_url` y `package_sha256`. `CANDIDATE`, `DEPRECATED` o `WITHDRAWN` no
   son instalables por este flujo. No resolver «última» por orden lexicográfico.
2. Recuperar el release exacto y consultar compatibilidad con la tupla completa:
   `template_id`, `version`, `component_id`, `component_version`, `contract_id`,
   `contract_version`, `schema_version` y esquema instalado cuando exista.
   Obtener versiones del destino real, no de un ejemplo o memoria histórica.
3. Exigir la misma tupla en la respuesta, `release_status=PUBLISHED`, `status=PASS`,
   `compatible=true`, `action=ALLOW`, referencia de evidencia y SHA-256.
   Una migración propuesta no autoriza ejecutarla; mantener backup y consentimiento.
4. Descargar solo por petición/alcance autorizado y verificar los bytes completos.
   El cliente rechaza redirecciones, URL ajena, cambios de hash y sobrescritura; una
   repetición con el mismo archivo íntegro devuelve `ALREADY_PRESENT`.
5. Antes de instalar, aplicar el preflight y el procedimiento existente del componente.
   La consulta de compatibilidad es una declaración del registro, no reproducción
   independiente ni instalación. No ejecutar scripts de paquetes al descargarlos.

## Ayudante local

`configure --config <archivo>` registra únicamente los endpoints locales. `list` consulta
el catálogo; `check` consulta release/compatibilidad; `download` añade `--output` y entrega
bytes verificados sin instalar; `verify` comprueba dos respuestas JSON ya recuperadas,
sin red. Pasar a los tres últimos comandos todos los identificadores/versiones mediante
`--template-id`, `--version`, `--component-id`, `--component-version`, `--contract-id`,
`--contract-version` y `--schema-version`. `verify` recibe `--release` y `--compatibility`.

El cliente limita los JSON a 2 MiB y la descarga a 400 MiB; son límites del cliente.
Una respuesta HTML, error de red o ausencia de release compatible mantiene la operación
bloqueada, sin eliminar funciones locales ni sustituir el catálogo por una candidata.
No declara READY el alta personal ni modifica permisos, cuentas, Apps o datos.
