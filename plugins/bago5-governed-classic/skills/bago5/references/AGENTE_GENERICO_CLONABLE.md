# Agente genérico clonable · BAGO5 0.4.39

## Alcance

Existe **una plantilla lógica** `bago5-generic`, no una flota preinstalada. Las copias son
**instancias de configuración independientes**, no workers ejecutados. El catálogo sigue
siendo `skills/bago5/references/CATALOGO_HABILIDADES.json`; no se duplica.

## Contrato

- La plantilla está deshabilitada, sin especialidad, modelo, proveedor, prompt, memoria,
  habilidades asignadas ni permisos de escritura. `sandboxMode=read-only` es metadato
  declarativo: el host DEBE aplicar aislamiento efectivo.
- `GET /agents` conserva `agents` y añade `templates` con la base virtual.
- `GET /agents/bago5-generic` devuelve la plantilla sin persistirla.
- `POST /agents/bago5-generic/duplicate` usa la ruta de duplicación ya existente;
  crea una definición nueva deshabilitada, sin heredar habilidades ni credenciales.
- `PUT /agents/{id}` acepta `skills: ["$bago5-..."]` y `skills: []` para retirar;
  solo identifica habilidades portables comprobadas en el catálogo y su `SKILL.md`.
- Duplicar una copia de la plantilla también produce otra copia limpia; los agentes
  antiguos mantienen su comportamiento de duplicación por compatibilidad.
- La revisión optimista existente sigue vigente; la instancia se registra en el
  almacén del proyecto que ya usa la API. No se introducen memorias ni registros globales.

## Límites de seguridad

Los *bindings* de habilidades NO conceden permisos, herramientas, conexiones MCP,
modelos, acceso a memorias, secretos ni ejecución. Una instancia no se debe activar
sin comprobar proyecto, misión, host, STOP, autorización y disponibilidad real de
herramientas. La ejecución nativa de múltiples agentes depende del host; este diff
no la añade ni la simula. Si se extrae el runtime fuera del plugin, una asignación
no vacía falla cerrada hasta que el catálogo canónico sea accesible.

## Aceptación mínima

1. La plantilla se consulta sin crear estado en disco.
2. Dos copias tienen identidad distinta y cero habilidades/permisos heredados.
3. Asignación selectiva; la segunda copia no recibe la habilidad de la primera.
4. Habilidad inexistente: error y estado inalterado.
5. Retirada de habilidades y conflicto de revisión probados.
6. Duplicar una instancia especializada nunca hereda la especialización.
7. Las operaciones anteriores de agentes heredados conservan su contrato.
8. En host real, comprobar que `enabled=False` impide ejecución y que STOP bloquea
   nuevas acciones; hasta entonces **NOT_RUN**, no VERIFICADO.
