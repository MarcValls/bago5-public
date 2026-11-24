# Frontera instrucción / contexto
El adaptador 0.1 concatenaba el snapshot de fuente con la orden. En la copia real, nombres como max_tokens y os.environ fueron clasificados como petición peligrosa. La ejecución falló antes de llamar al host (evidence/development/01_native_refusal).

La versión 0.2 mantiene el clasificador nativo sobre la instrucción completa de la misión. Añade snapshot, memoria y observación como datos identificados dentro del ContextEnvelope nativo mediante un mixin explícito del adaptador. No cambia el clasificador ni SPBE, no oculta la orden ni habilita una operación rechazada. Los datos incluidos no conceden autoridad: cada acción sigue pasando por las allowlists, precondiciones SHA y permisos de un uso.

El hash del paquete de contexto figura en la solicitud, en el envelope y en la traza. El presupuesto se recalcula; si no cabe se bloquea. No se afirma inmunidad general a prompt injection. El texto de código se entrega íntegro, sin redactar identificadores para eludir un filtro.
