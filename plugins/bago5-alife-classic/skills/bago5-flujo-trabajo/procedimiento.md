[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

Aplicar [bago5](../bago5/SKILL.md) y su contexto de memoria. Este router no crea objetivos, instala servicios ni concede permisos. Los identificadores historicos de modulos de la politica se traducen a destinos incluidos; no requieren instalaciones antiguas.

Consultar [politica](references/route-policy.json). Intentos: question (sin especialistas), repository, goal, phased, app_game, repair y ui. Cargar solo los destinos seleccionados y recursos necesarios. Anadir --include solo si el alcance pedido lo necesita y la politica lo permite.

Si el trabajo pertenece a un plan por fases, leer la política y las habilidades necesarias para comprobar viabilidad; antes de convertir la ruta en una selección operativa, asignación o modificación, exigir el [preflight vigente de esa fase](../bago5-plan-por-fases/references/phase-preflight.md). El recibo de ruta no sustituye ese preflight. Identificar y comunicar de antemano cualquier cambio Codex↔Work o intervención humana necesaria para ejecutar, verificar y entregar la fase.

Con Python realmente disponible:

```text
python <skill-root>/scripts/route_suite.py --intent <intento> --reason "<motivo verificable>" --request-id <id-estable> [--include <modulo>] [--receipt <destino-autorizado>]
```

El recibo incluye politica/hash, seleccion, exclusiones y rutas. Rechaza combinaciones no permitidas, IDs vacios y destinos ausentes. Un recibo existente nunca se sobrescribe. Crear un archivo solo en el destino autorizado; sin --receipt devuelve JSON por stdout.

En GPT Classic sin ejecucion, aplicar la politica de forma conversacional, indicar seleccion y motivo, y marcar recibo de script NOT_RUN. No fabricar hashes ni simular ejecucion. La seleccion es orientativa: no bloquea otras skills a nivel del host.

Preservar contexto del proyecto; resolver conflictos segun instrucciones actuales del usuario y proyecto. Un recibo de ruta no demuestra ejecucion, autorizacion, aislamiento, verificacion del producto ni activacion automatica de subskills.

Para añadir un especialista con `--include`, usa su nombre público, por ejemplo `bago5-plan-por-fases`. En el recibo, `selected_skills` contiene las invocaciones con el prefijo `$bago5-`. Los campos de módulos v1 conservan sus identificadores para clientes existentes. El [perfil opcional para Codex CLI](references/codex-profile.md) permite comprobar el catálogo de habilidades visible en una sesión dedicada.
