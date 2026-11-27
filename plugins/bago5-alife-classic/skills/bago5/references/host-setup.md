# Configurar BAGO5 y ALIFE en cada anfitrión

Usar esta referencia al instalar, conectar, recuperar acceso o trasladar el trabajo entre ChatGPT, Codex y GitHub Copilot CLI. Conservar el [recorrido de incorporación](onboarding.md) y su paso actual. El servicio ALIFE es compartido; instalación, catálogo de herramientas y autorización se verifican por anfitrión.

## Contenido

- [Comprobación previa](#comprobación-previa).
- [ChatGPT y Platform](#chatgpt-y-platform).
- [Codex](#codex).
- [GitHub Copilot CLI](#github-copilot-cli).
- [Cambio de anfitrión y recuperación](#cambio-de-anfitrión-y-recuperación).
- [Fuentes y compatibilidad](#fuentes-y-compatibilidad).

## Comprobación previa

Comprobar versión instalada, manifiesto y catálogo real. Descubrir las herramientas diferidas y leer su firma antes de usar un nombre citado en la guía. Una habilidad describe procedimientos; no instala un cliente, un conector, hooks ni un proceso permanente. La declaración `onboardingSkill` ofrece una entrada de configuración donde el anfitrión la admita; no acredita que se ejecute automáticamente al instalar.

Antes de cambiar configuración, leer la configuración existente y la ayuda de esa versión. Conservar nombres, servidores, rutas y decisiones de usuario. Reutilizar una conexión válida; no añadir otra con el mismo endpoint por seguir un ejemplo. Distinguir una variante compatible del paquete, una conexión configurada, una herramienta expuesta y una operación autorizada.

| Recurso ALIFE | Responsabilidad | Comprobación |
|---|---|---|
| `https://alifememories.com/mcp` | Proyectos, recuerdos, objetivos, planes, Vault y relaciones que el catálogo vigente exponga | `get_memory_identity`; operación de lectura; `get_vault_identity` cuando haya archivos |
| `https://alifememories.com/mcp/gestor` | Cuenta, gestión de memorias, catálogo y Guardia según herramientas disponibles | Identidad propia del gestor y scopes administrativos pertinentes |

Los tokens pertenecen al cliente y al recurso que los emitió. No reenviarlos entre recursos ni copiarlos a otro anfitrión. Instalar BAGO5 no crea una cuenta ALIFE. Crear una memoria no abre sus permisos de acceso y seleccionar un espacio en el gestor no cambia un grant de contenido existente.

La variante local usa registro dinámico de clientes (DCR) para ambos recursos, con callbacks propios del anfitrión. No reutilizar el cliente proporcionado de Platform. Las extensiones `com.openai` solo tienen efecto en los anfitriones que las admiten: en Copilot, comprobar su OAuth nativo y los permisos efectivos. Si el anfitrión no completa un desafío de scopes incremental, reautorizar explícitamente por su flujo oficial y releer la identidad antes de continuar.

No ejecutar instalaciones, modificar perfiles ni añadir conexiones por cargar esta referencia. Hacerlo solo cuando el encargo lo autorice y el destino esté identificado. No introducir credenciales en el manifiesto, archivos de proyecto, comandos visibles, ejemplos, registros o el chat. La persona completa identidad y consentimiento en la superficie oficial.

## ChatGPT y Platform

Si BAGO5 ya aparece en el chat, continuar allí. Si la persona pide instalarlo, usar [Plugins de ChatGPT](https://chatgpt.com/plugins) y la ficha BAGO5 ALIFE Classic accesible a esa cuenta. Comprobar la identidad y disponibilidad de la ficha; no ofrecer IDs o complementos privados del desarrollador como dependencias del usuario nuevo.

El paquete de Platform con un único servidor MCP de ALIFE usa `/mcp`. Conservar su cliente configurado y la conexión existente. Esa conexión permite solo las herramientas y scopes que el servicio y el anfitrión expongan. El gestor `/mcp/gestor` no queda conectado por mencionarlo en las instrucciones ni puede añadirse como si formara parte del mismo recurso OAuth. Completar la gestión de espacios por la web de ALIFE cuando falte su capacidad en el chat.

Para conexión o reconexión solicitada, usar `alife_conectar_memoria` si está disponible. Si el anfitrión proporciona una acción oficial de autenticación con identificadores de conector, pasar los identificadores exactos de su respuesta; no fabricarlos. En otro caso, guiar a la ficha del complemento instalado y a la acción de conectar o reconectar que realmente muestre la interfaz. No confundir la ficha del paquete con una URL OAuth comprobada.

La persona inicia sesión en ALIFE, selecciona la memoria y acepta los permisos necesarios en el flujo generado por ChatGPT. Si aparece otra cuenta, resolver la identidad en el propio flujo antes de continuar; no sustituir sesiones ni reutilizar cookies. Al regresar al mismo chat, releer identidad y ejecutar una lectura autorizada. Si los permisos del espacio están cerrados, seguir el paso correspondiente de [onboarding](onboarding.md#permisos-y-conexión).

Para Vault, buscar sus operaciones en todo el catálogo accesible. Si están disponibles pero piden autenticación, resolver esa conexión concreta; no anunciar que faltan herramientas ni prestar la identidad de otra aplicación. Si realmente no están expuestas, distinguirlo de una carencia del servidor y conservar las funciones de memoria que sí están comprobadas.

## Codex

Determinar qué Codex está usando la persona y dónde se ejecuta. La disponibilidad local de una CLI no concede acceso a su equipo. Cuando exista ejecución autorizada, consultar `codex --version`, `codex mcp --help` y la ayuda de plugins de esa versión antes de adaptar la configuración. Usar la variante distribuida compatible y su origen comprobado; no asumir que un ZIP para revisión de ChatGPT instala por sí mismo todas las capacidades de Codex.

Si el paquete ya registra el servidor, consultar el catálogo y reutilizarlo. `codex mcp list` y la vista `/mcp` de la interfaz permiten revisar conexiones en las versiones que lo admitan. Si falta una conexión y el usuario pidió añadirla, la forma documentada de una entrada HTTP es:

```sh
codex mcp add alife-memoria-viva --url https://alifememories.com/mcp
codex mcp login alife-memoria-viva --scopes memory.read
```

Estos comandos son ejemplos condicionados a la ayuda de la versión instalada; no ejecutarlos automáticamente ni duplicar una entrada creada por el plugin. Usar el nombre real de la conexión si difiere. Ampliar los scopes solicitados únicamente para las capacidades elegidas: `memory.write`, `vault.read` o `vault.write`. Verificar el consentimiento efectivo; la lista pedida no demuestra concesión.

Dejar que Codex gestione el flujo OAuth, PKCE, el retorno y el almacenamiento privado de credenciales. Si necesita registro de cliente, consultar los metadatos actuales del servidor y el soporte de esa versión. No copiar el cliente o token de ChatGPT para conseguir una conexión. Si el servicio no ofrece el mecanismo requerido, registrar esa incompatibilidad concreta y mantener el trabajo independiente.

La conexión del gestor, cuando sea necesaria y admisible, es otra entrada apuntando a `/mcp/gestor`, con identidad y consentimiento propios. Usar `manager.read` y pedir `manager.memories` solo si la persona quiere crear o seleccionar memorias por ese canal. No pedir `manager.write` o `catalog.admin` para resolver una lectura ordinaria. Si no existe gestor utilizable, usar la web para esa gestión y volver a comprobar la memoria de contenido.

Después de conectar, ejecutar `get_memory_identity` y una lectura real desde Codex. La salida del comando de login o del listado de servidores no acredita esa lectura. Hooks, receptor Guardia, herramientas de terminal y permisos del proyecto tienen configuración y autoridad separadas; no activarlos como parte implícita de conectar memoria.

## GitHub Copilot CLI

Comprobar que se trata de Copilot CLI y verificar su versión, ayuda y configuración cuando haya acceso autorizado. No confundirlo con Copilot en otra interfaz. Leer el esquema de plugins que admita esa versión antes de instalar o adaptar un paquete; comprobar los campos de manifiesto y `mcp.json` y preservar los componentes existentes.

El formato Agent Plugins usa habilidades y descriptores MCP, pero las extensiones específicas de OpenAI no conceden autenticación ni garantizan comportamiento en Copilot. Reutilizar una variante Copilot realmente distribuida y verificada cuando exista. Si falta, explicar la adaptación necesaria sobre una copia autorizada; no afirmar que está instalada ni incorporar claves personales al paquete.

Si la versión admite instalar plugins, `copilot plugin install` puede aceptar un origen de repositorio con ruta o una carpeta local. Obtener el origen exacto de la distribución antes de completar el comando; no inventar una ruta de release ni instalar desde una ubicación incidental. Revisar `copilot plugin --help`, el listado de plugins y `copilot mcp list`. Si el servidor procede ya del plugin, usar esa entrada.

Para una conexión HTTP ausente que la persona haya solicitado, comprobar primero la ayuda. La sintaxis documentada incluye:

```sh
copilot mcp add --transport http alife-memoria-viva https://alifememories.com/mcp
copilot mcp get alife-memoria-viva
```

La acción interactiva `/mcp auth alife-memoria-viva`, cuando la versión la ofrezca, inicia OAuth. Conservar el nombre real y completar la identidad y los permisos en ALIFE. Consultar el catálogo y los scopes efectivamente concedidos después de autorizar. Un descriptor «Enabled» o «Source: Plugin» acredita configuración, no acceso a la memoria ni transferencia de archivos.

El servidor puede anunciar registro dinámico de clientes; comprobar esa metadata antes de diagnosticar su ausencia. El anuncio de DCR tampoco prueba que la versión de Copilot complete el flujo. No suponer soporte CIMD, renovación mediante refresh tokens o callbacks no anunciados. Si al caducar se necesita consentimiento nuevo, usar el flujo oficial de Copilot y verificar identidad otra vez.

Comprobar lectura, escritura autorizada y Vault por separado con el [recorrido común](onboarding.md#comprobación-de-memoria-y-vault). Para gestor, aplicar la separación de recurso y permiso anterior únicamente si Copilot expone esa conexión. No instalar modelos, runtimes ni agentes locales para suplir una autorización pendiente.

## Cambio de anfitrión y recuperación

Conservar un relevo autorizado con objetivo, memoria/proyecto, fuentes versionadas, permisos observados, trabajo realizado, incertidumbres y siguiente paso. Excluir secretos. La memoria o el archivo de relevo no concede al receptor la autoridad ni la sesión del emisor.

En el receptor, recuperar las capacidades reales, comprobar identidad y `memory_id`, leer el relevo y contrastar las revisiones pertinentes. Recuperar la fuente no inicia una ejecución detenida. Ante STOP, revocación o diferencia de destino, mantener la barrera correspondiente; no usar otro cliente para eludirla.

Si se interrumpe el alta o la conexión, consultar primero el estado que realmente ofrezca el servicio. Mantener la solicitud idempotente y los recibos de operaciones inciertas. Reanudar desde el último resultado comprobado sin crear cuentas, memorias o conexiones duplicadas. La preferencia «sin memoria» se respeta también al cambiar de cliente hasta que la persona decida conectarla.

## Fuentes y compatibilidad

Revisar estas fuentes oficiales y la ayuda instalada cuando se prepare una configuración; la compatibilidad depende de la versión y del servicio observado:

- [MCP en Codex CLI](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
- [Referencia de comandos de GitHub Copilot CLI](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference).
- [Referencia de plugins de GitHub Copilot CLI](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference).
- [Directorio de plugins de ChatGPT](https://chatgpt.com/plugins).
- [Metadatos OAuth de ALIFE](https://alifememories.com/.well-known/oauth-authorization-server) y [recurso de memoria](https://alifememories.com/.well-known/oauth-protected-resource/mcp).
- Contratos del servidor ALIFE: `BAGO5-ONBOARDING-002`, `NATIVE-TOOLS-001` y `VAULT-OAUTH`; contrastar sus descriptores y respuestas desplegados.

No declarar igualdad funcional entre ChatGPT, Codex y Copilot por compartir MCP. Informar por anfitrión de paquete cargado, herramienta expuesta, identidad, permisos, operación ejecutada y resultado releído. Las instrucciones de esta referencia no son evidencia de una prueba en un usuario nuevo.
