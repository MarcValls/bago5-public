# BAGO5 Classic para Codex

BAGO5 Classic 0.4.59 te ayuda a organizar un proyecto en fases, ejecutar tareas y comprobar el resultado. Puedes empezar en una carpeta local y conectar tu propia Memoria Viva de ALIFE cuando la necesites.

## Instalar en Windows con doble clic

1. [Descarga Instalar-BAGO5-Classic.cmd](https://github.com/MarcValls/bago5-public/releases/download/v0.4.59/Instalar-BAGO5-Classic.cmd) y ábrelo con doble clic. Windows abre una terminal. Si falta Git o Codex CLI, el instalador te ofrece instalar cada herramienta con WinGet y te pide permiso. También ofrece Python si lo necesitas para los hooks y auxiliares locales.
2. Elige tu carpeta de trabajo. Codex se abre en modo de lectura y te explica los cambios que necesita hacer en tu perfil. Si es tu primera sesión, inicia sesión en el propio Codex. Autoriza la instalación cuando quieras continuar.
3. Cuando Codex confirme la instalación, escribe `/quit`. El instalador comprueba la versión y te ofrece abrir una sesión nueva en tu carpeta con Classic cargado.

## Instalar desde la terminal

Con Git y Codex CLI instalados, ejecuta estas órdenes en PowerShell, macOS o Linux. La etiqueta fija la versión que vas a recibir.

```sh
codex plugin marketplace add MarcValls/bago5-public@v0.4.59
codex plugin add bago5-governed-classic@bago5-public-tools
codex plugin list --marketplace bago5-public-tools --json
```

En `installed` busca `bago5-governed-classic@bago5-public-tools`, versión `0.4.59`, con `enabled: true`. En Windows también puedes ejecutar `.\Instalar-BAGO5-Classic.cmd --solo-instalar` para instalar desde la terminal con confirmación y sin abrir el chat.

Abre Codex en la carpeta de tu proyecto y escribe:

```text
Usa $bago5 para ayudarme a organizar este proyecto. Muéstrame el primer paso.
```

## Herramientas opcionales

- Las habilidades de planificación y revisión funcionan con Codex. Para los auxiliares de Python y los hooks locales necesitas Python 3.11 o posterior. En Windows comprueba `py -3 --version`. Codex gestiona la confianza de los hooks.
- Si quieres memoria persistente, elige tu espacio en [ALIFE Memoria Viva](https://alifememories.com/memoria-viva) y autoriza el conector en tu cliente. La instalación del plugin y el acceso a tu cuenta ALIFE son decisiones separadas.
- El paquete público distribuye las habilidades Classic, sus scripts portables y los descriptores MCP. RC4 y los flujos que usan TaskStore necesitan una instalación externa identificada de BAGO Operating Suite. Los paquetes históricos, las fichas privadas, los datos de usuarios y los binarios del intérprete se excluyen de esta edición.

## Instalaciones existentes y desinstalación

Si ya registraste el catálogo siguiendo la guía de 0.1.2, actualízalo con `codex plugin marketplace upgrade bago5-public-tools` y ejecuta la orden `codex plugin add` de arriba. Si fijaste expresamente el catálogo a una etiqueta antigua, conserva el nombre de esa etiqueta antes de cambiarla. Puedes registrar la nueva con `codex plugin marketplace remove bago5-public-tools` y la primera orden de instalación. Para volver, registra tu etiqueta anterior.

Classic tiene su propio identificador. Si ya usas BAGO5 Público 0.1.2, puedes conservarlo junto a Classic. Para quitar únicamente Classic:

```sh
codex plugin remove bago5-governed-classic@bago5-public-tools
```

[Descarga del paquete y sumas SHA-256](https://github.com/MarcValls/bago5-public/releases/tag/v0.4.59) · [Guía de BAGO5 Público 0.1.2](plugins/bago5-public/README.md)
