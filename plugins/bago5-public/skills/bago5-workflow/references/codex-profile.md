# Perfil CLI opcional

Requiere Python 3.9 o posterior y un Codex CLI cuyo catálogo completo se pueda inspeccionar. Instala primero la habilidad en el host seleccionado. Comprueba que el ejecutable nativo admite `--no-daemon`, perfiles y `debug prompt-input`. El perfil se crea únicamente al invocar este procedimiento.

Desde la carpeta de esta habilidad:

```text
python scripts/codex_suite.py prepare --codex-home DIRECTORIO_AUTORIZADO --skill-md SKILL.md
```

Se lee el catálogo y se genera un perfil distinto de la configuración global. Solo la entrada workflow seleccionada queda habilitada en ese perfil. Se comprueban el catálogo y el hash del perfil final. Las entradas que resuelva el selector pueden leerse con las capacidades disponibles del host; el recibo por sí mismo no ejecuta especialistas. Un catálogo truncado, una ruta ambigua o un formato incompatible interrumpen la preparación. Para iniciar una sesión interactiva con ese perfil, sustituye `prepare` por `run`. Un perfil que filtre habilidades conserva los permisos y la política del host.
