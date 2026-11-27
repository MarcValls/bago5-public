# BAGO 4.11.10 — subconjunto con reparación local

Este runtime es opcional dentro de BAGO Operating Suite 1.4.1 REPAIR RC1.
Codex conserva las instrucciones, los permisos y la autoridad del proyecto.
Instalar el paquete no inicia agentes, servicios ni procesos de fondo.

## Identidad y procedencia

La entrega original declara BAGO 4.11.10, repositorio `MarcValls/BAGO`, commit
`5fb6f2f0c57f29de1b42bbb2efb4a57c86aa032d`. Su
SOURCE_LOCK.json (motor local independiente) se conserva íntegro como registro histórico
de 462 archivos. La consulta de ese commit durante esta reparación devolvió
`404: No commit found for the ref`; no se afirma haber recuperado desde él los
contratos ausentes.

Los siete contratos se obtuvieron del mismo repositorio en el commit fijado
[`f3804a7e9333607561d28fd5075569e725aa0bb0`](https://github.com/MarcValls/BAGO/tree/f3804a7e9333607561d28fd5075569e725aa0bb0/backend/.bago/contracts).
El parser `effect_registry.py` de ese commit coincide byte a byte con el incluido
en el ZIP original. Se comprobaron SHA-256 y Git blob de cada contrato, y se
ensayó su uso por los recorridos reparados. Esa compatibilidad acotada no
demuestra equivalencia de dos releases completas.

REPAIR_PROVENANCE.json (motor local independiente) identifica los archivos
recuperados y cada parche local, con hashes originales y posteriores.
El verificador del paquete comprueba los originales intactos contra el lock,
los parches contra su procedencia y los contratos contra sus identidades fijadas.
No se presenta este árbol derivado como un checkout intacto de upstream.
La licencia MIT original sigue incluida en [LICENSE](LICENSE).

## Frontera verificada

- Carga del registro de efectos y persistencia a través del gateway local real.
- Escritura fuera de una raíz autorizada rechazada en la prueba correspondiente.
- Creación y ejecución directa del agente espiral, dos ciclos en procesos nuevos,
  avance de fase, readback y puertas cerradas entre skills.
- Observaciones persistentes que condicionan `plan()` y `act()` tras reinicio.
- Promoción de patrones, errores visibles y validación de registros.
- Puente RL, registro canónico, entrenamiento BC, guardado y recarga con fixtures.
- Evaluación numérica acotada; sondeo predeterminado marcado sin evaluación de mejora.

Los tests están en `repair-tests` en la raíz de la distribución. No forman parte
del payload que copia el instalador. La evidencia completa y los comandos están
en el pack de continuidad y en las notas de reparación de la distribución.

## Límites operativos

El agente espiral conserva reglas y puntuaciones limitadas; no adquiere nuevas
skills por sí mismo. Su puerta se aplica a transiciones entre skills, por lo que
la primera skill puede ejecutarse antes de una denegación posterior. Sus registros
auxiliares y `state.json` no constituyen una transacción única.

La adaptación por resultados es una regla sobre historial. Los tests no demuestran
escritores concurrentes ni recuperación ante cortes de energía. BC aprende datos
sintéticos; la exclusión de vectores idénticos entre entrenamiento y evaluación
no establece independencia estadística ni mejora en tareas reales.

`RLBridge` conserva los modos `shadow` y `off`, con `can_execute=False`.
Ahora usa el mismo `state_root()` que el entrenador. No migra ni elimina registros
históricos de `.gabo/state`. El reentrenamiento de intenciones sigue sin implementar
y se informa como tal. `auto_evolve()` no debe interpretarse como éxito global
si alguna parte no está implementada o ha fallado.

No se han acreditado la CLI completa, la API, proveedores, Windows, un servicio
continuo ni la integración real con BAGO5/ADL. Las dependencias generales del
runtime están declaradas en [backend/requirements-runtime.txt](backend/requirements-runtime.txt);
el instalador no las instala. Los recorridos de esta reparación usan estado temporal
y datos de prueba, sin historiales personales ni credenciales.

## Contenido conservado

Se conserva el subconjunto de backend, contexto, memoria, herramientas y auditor
de huérfanos de la entrega. No incluye la UI de escritorio ni assets de Electron.
El auditor de huérfanos sigue siendo heurístico; sus resultados no sustituyen una
prueba del recorrido funcional. Para claims de capacidad, vincule siempre la
operación concreta, su fuente y la evidencia de ejecución correspondiente.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
