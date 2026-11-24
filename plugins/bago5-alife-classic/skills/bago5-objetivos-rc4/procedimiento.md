[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

Aplicar [bago5](../bago5/SKILL.md), el proyecto actual y [controlador unico](../bago5/references/controller-selection.md). Este puente usa TaskStore Suite, no teamctl. No equivale a Goal nativo de ChatGPT/Codex ni otorga continuidad autonoma.

Motor: [goal_bridge.py](../../optional-runtime/rc4-goals/goal_bridge.py), worker, cancelacion y contrato incluidos. Leer [contrato RC4](../../optional-runtime/rc4-goals/README.md). Los dictamenes del origen y evidencias heredadas no validan esta adaptacion a Suite1.4.8.

Siempre indicar --workspace, --state-root y --suite con rutas explicitas y autorizadas. La Suite incluida esta en <plugin-root>/optional-runtime/bago-operating-suite. Empezar por doctor o resume, ambos resumen sin ejecutar ni reanudar. No usar los lanzadores historicos .cmd ni verify_release.py como instaladores/verificadores del complemento unificado.

run/dispatch requieren --approve-run y Codex CLI real; solo dentro del alcance autorizado y tras pruebas de compatibilidad del binding concreto. Dispatch admite una ronda y supervisa un worker read-only; retorno correcto no consume evidencia ni cierra TaskStore. STOP documental, STOP persistido y cancelacion de proceso son estados diferentes. Un latch de recuperacion impide nueva admision. task-resume necesita objetivo y motivo explicitos; no reanuda otros ledgers ni abre ronda. Nunca eliminar marcadores para forzar avance.

En GPT Classic esta ruta requiere un conector de ejecucion hacia el runtime Windows/Codex. Sin el, puede interpretar el contrato y preparar handoff, pero despacho/STOP externo/recuperacion quedan NOT_RUN. El control Windows Job no abarca procesos de servicios externos ni promete cancelacion instantanea. Linux/macOS requieren pruebas propias.
