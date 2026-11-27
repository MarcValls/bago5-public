[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Auditoría arquitectónica vigente

Audita la candidata y el repositorio accesible ahora. Registra cwd, branch, HEAD, estado dirty, alcance, fuentes consultadas y criterios de aceptación. Lee instrucciones activas y sigue los entrypoints reales entre contratos, módulos, imports, rutas y pruebas.

Clasifica afirmaciones como comprobadas, históricas, inferidas o no recuperadas. Un índice estático, mock, scaffold, hash o paquete congelado no demuestra funcionamiento actual. La evidencia histórica solo es contexto comparativo cuando su archivo está disponible; no la declares canon ni la presentes como auditoría live.

No ejecutes binarios ni scripts desconocidos durante una auditoría de solo lectura. No edites la candidata. Para cada hallazgo incluye ruta/línea, evidencia, impacto, límite y prioridad. Si no tienes acceso al repo o a los archivos, reporta exactamente lo que falta y deja la comprobación NOT_RUN.
