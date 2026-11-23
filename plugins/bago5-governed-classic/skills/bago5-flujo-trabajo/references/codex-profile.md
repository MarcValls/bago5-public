# Perfil de Codex CLI para BAGO5 Workflow

El perfil muestra únicamente la entrada `bago5-flujo-trabajo` en el catálogo de habilidades de Codex. El catálogo puede mostrar su nombre cualificado `bago5-governed-classic:bago5-flujo-trabajo`. La identidad incluye la ruta exacta del archivo instalado para distinguir copias de distintos mercados. El perfil afecta a la selección de habilidades de la CLI. Los permisos del host, las herramientas, la red y el acceso a memorias se comprueban por separado.

Desde la carpeta instalada de la habilidad, con Python 3.9 o posterior y el ejecutable nativo de Codex CLI:

```text
python scripts/codex_suite.py prepare
python scripts/codex_suite.py run --prompt "Selecciona el flujo para esta tarea."
```

`prepare` usa `CODEX_HOME` (o el directorio de configuración habitual). Con `--codex-home <directorio>` puedes elegir un perfil de usuario de pruebas existente. Si el ejecutable está fuera de PATH, indica `--codex <ruta-al-ejecutable>`. Si pruebas el script desde un checkout, `--skill-md <SKILL.md-instalado>` selecciona la copia que Codex realmente descubre. En Windows se usa el binario nativo, incluido el distribuido por npm.

La CLI debe admitir `--no-daemon`, perfiles V2, `debug prompt-input` y las entradas `skills.config` por ruta. El script inventaría el catálogo de la misma carpeta de trabajo desde la que se iniciará la sesión. Rechaza catálogos incompletos o ambiguos y prueba un perfil provisional. Solo al comprobar que queda una habilidad crea un archivo `bago5-workflow-<huella>.config.toml` mediante un enlace físico exclusivo en el mismo sistema de archivos. Comprueba otra vez el perfil final antes de iniciar Codex. Una repetición con el mismo catálogo reutiliza un perfil idéntico. Un cambio de catálogo puede producir un nombre nuevo. Una colisión con un perfil de distinto contenido cancela la operación.

`run` abre una sesión interactiva con la configuración de autenticación del directorio seleccionado. El recibo JSON de `prepare` acredita el nombre, SHA-256 y recuentos de la comprobación local. La consulta de descubrimiento es local a la CLI y no envía un prompt de trabajo al modelo. Para probar los rechazos sin iniciar una sesión:

```text
python -B -m unittest discover -s tests -p test_codex_suite.py
```
