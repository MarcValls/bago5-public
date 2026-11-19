# BAGO5 Público

BAGO5 Público reúne 59 habilidades en español para planificar, desarrollar y comprobar trabajos en Codex. Esta guía te acompaña desde la instalación hasta tu primer guion para una exposición.

## 1. Encuentra el plugin

- **Desde Alife Memories**, abre «Plugin BAGO5». Allí tienes el botón de descarga y el enlace al código y a la guía de GitHub. [Abrir la página del plugin](https://alifememories.com/plugin/)
- **Desde GitHub**, puedes seguir los pasos de instalación de este README directamente. Si quieres examinar los archivos, descarga el ZIP y su suma SHA-256 desde la última versión. [Repositorio](https://github.com/MarcValls/bago5-public) · [ZIP](https://github.com/MarcValls/bago5-public/releases/latest/download/bago5-public.zip) · [SHA-256](https://github.com/MarcValls/bago5-public/releases/latest/download/bago5-public.zip.sha256)
- **Si ya tienes el ZIP**, puedes extraerlo en una carpeta nueva y abrir `README.md` para leer esta misma guía. Extraerlo solo permite inspeccionar su contenido. La instalación en Codex se hace con los comandos del paso 2.

## 2. Instala el plugin en Codex

Abre **PowerShell** en Windows o **Terminal** en macOS o Linux. Necesitas Git, Codex CLI y acceso a GitHub. Escribe `git --version` y `codex --version` para comprobar que ambas herramientas están disponibles. Si falta alguna, instala la que te indique la terminal antes de continuar.

Ejecuta estas dos órdenes, una por línea:

```sh
codex plugin marketplace add MarcValls/bago5-public
codex plugin add bago5-public@bago5-public-tools
```

La primera registra el catálogo de BAGO5 Público. La segunda instala el plugin desde ese catálogo.

## 3. Abre tu carpeta de trabajo

Elige una carpeta donde quieras trabajar, por ejemplo una carpeta vacía llamada `exposicion-agua`. Abre una terminal en ella o usa `cd` para entrar en la ruta de la carpeta. Allí escribe `codex` y pulsa Intro para iniciar **una sesión nueva**. Si Codex solicita iniciar sesión, completa ese paso en tu propio cliente. A partir de aquí escribe las peticiones en el chat de Codex.

## 4. Prepara una exposición de cinco minutos sobre el ciclo del agua

1. **Pide un guion en tres partes.** Copia esta petición:

   > Usa $bago5-govern para ayudarme a preparar una exposición oral de cinco minutos sobre el ciclo del agua para mi clase. Dame un guion en tres partes: una apertura que despierte curiosidad, una explicación con un ejemplo y un cierre que resuma la idea principal. Indica el tiempo aproximado de cada parte.

2. **Lee el guion en voz alta** y cronometra cuánto tardas. Anota dónde te cuesta seguir la explicación o qué parte necesitas acortar. Tu ritmo real permite ajustar el texto.

3. **Pide que compruebe duración y contenidos.** Sustituye el espacio en blanco por tu tiempo:

   > Usa $bago5-final-verifier para revisar este guion. Al leerlo he tardado __ minutos y segundos. Comprueba si las tres partes suman cinco minutos y si explico bien la evaporación, la condensación, la precipitación y el retorno del agua a ríos, suelos y mares. Si algo falla, señala el fragmento y propón un ajuste que pueda ensayar.

4. **Si quieres conservarlo**, pide a Codex: «Guarda la versión revisada en un archivo nuevo llamado `guion-ciclo-del-agua.md` dentro de esta carpeta y comprueba que puedo abrirlo». Si ya existe ese nombre, elige otro para preservar tu copia.

Al terminar tendrás un guion con tres partes, una revisión de los conceptos y una estimación de la duración. Repite la lectura con cronómetro para comprobar si el ajuste funciona con tu ritmo. Si pediste guardarlo, podrás volver a abrir el archivo desde tu carpeta.

El ejemplo funciona sin conectar una memoria externa. Si quieres usar una, configura su conector y los permisos de lectura o escritura para la cuenta y el proyecto elegidos. Otras habilidades disponibles son `$bago5-goal` para fijar criterios y `$bago5-workflow` para seleccionar especialistas. Para pedir ayuda, describe los pasos con datos de ejemplo. [Abrir una incidencia](https://github.com/MarcValls/bago5-public/issues)
