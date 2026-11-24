# Incidencias, verificación diferencial y decisiones

Identidad de la base: `BAGO-SUITE-147-BAGO-SKILL-RC2` · versión 1.4.7 · candidato `CONTEXT-LIFECYCLE-NATIVE-RC2`.

Los cinco errores constituyen el alcance de esta reparación. Los hallazgos F01–F07 de la batería de **simulación de runtime** son otro inventario y siguen su propio dictamen; esta derivada no los considera resueltos automáticamente.

**Reparación:** puente externo, deliberadamente fuera del directorio de la skill para no invalidar el control estricto `suite_identity.current_identity()`. Los planes TaskStore siguen sujetos al motor original y a su permiso de host.

**Evidencias:** `evidencias/TEST_17_RESULTADOS.txt`: 17 pruebas PASS en Linux, con procesos mock reales; `BASE_CONTEXT_TESTS.txt`: 30 PASS + 8 subtests; `BASE_COGNITIVE_TESTS.txt`: 18 PASS. Las ejecuciones de batería completa y de session-context excedieron el tiempo disponible y se conservan sin atribuir PASS. `TEST_PRELIMINAR.txt` conserva el antecedente de un `ResourceWarning` detectado en el *test harness*, corregido al cerrar explícitamente una conexión antes de repetir los tests.

**No verificado:** Windows real, `codex.cmd` real, contención de procesos descendientes bajo Windows Job Object, versiones RC1 incompletas por ausencia de bytes de origen, flujo de orquestación integral y agentes remotos. No se presenta sustitución de los antiguos puentes ni actualización de una instalación existente.

**Criterio de GO:** (i) 17 tests de reparación PASS en Windows; (ii) lanzamiento `.cmd` positivo y negativo con `%ERRORLEVEL%`; (iii) las cuatro reproducciones WinError 32 finalizan sin fugas; (iv) confrontación funcional con RC1 disponible; (v) una operación Codex CLI real en TaskStore dentro de alcance aprobado y STOP efectivo. Conservar evidencias y dictamen independiente.

**Estado:** IMPLEMENTADO puente externo, VERIFICADO parcialmente en Linux, NO_COMPROBADO Windows/Codex real. Dictamen: **NO_GO para orquestación completa**.
