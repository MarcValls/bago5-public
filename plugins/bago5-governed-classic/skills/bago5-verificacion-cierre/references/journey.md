# Contrastar un recorrido

Antes de ejecutar, describe el recorrido pedido en un plan JSON. Anota el destino exacto y una revisión o huella de la candidata. `steps` contiene solo los hitos obligatorios solicitados. Para cada uno fija un nombre estable (`step`), el rol, una referencia sin datos personales al recurso, el tipo de operación (`page`, `action`, `write` o `reread`) y una observación esperada verificable (`expect`). Si un paso depende de otro, utiliza `after` con el nombre del precedente. Para una escritura refleja la autorización ya vigente mediante `write_authorized`. El plan documenta el alcance; no concede acceso.

Registra cada hito observado como un objeto en una lista JSON separada. Usa `id` único, `step`, `destination`, `candidate`, `role`, `resource`, `operation`, `result`, `observed`, `run`, `evidence` y `mode`. En la secuencia, `previous_receipt` enlaza el recibo anterior y `run` identifica el mismo recorrido aunque el servicio renueve su sesión al autenticar. Usa una referencia de prueba como identificador del recorrido; conserva cookies, tokens y datos personales fuera del recibo.

Para una página puede utilizarse una lectura HTTP real (`live_http`) que contraste su contenido. Las acciones funcionales requieren una interacción efectiva (`live_interaction`) mediante el cliente pertinente al encargo. Si el resultado es `FAIL`, `NOT_RUN` o `INCONCLUSIVE`, añade la causa en `reason`. El comprobador compara el valor observado con el esperado de manera exacta. Elige valores estables que puedas obtener de la observación y conserva una referencia a la fuente.

Desde esta habilidad se pueden contrastar los dos archivos con:

```sh
python scripts/assess_journey.py plan.json recibos.json
```

El código de salida es 0 con cobertura de recibos completa, 1 con hitos pendientes y 2 si la entrada es inválida. El resultado solo corresponde a la consistencia y cobertura de los recibos. Inspecciona su procedencia y contrasta las fuentes reales antes de afirmar una verificación del producto.

La [regresión sintética](../tests/test_assess_journey.py) ilustra un recorrido que pasa por la portada, la autenticación, la entrada a una memoria y la navegación al siguiente recuerdo. Incluye una variante de escritura y relectura para los encargos que lo piden. Se ejecuta con `python -B tests/test_assess_journey.py` y no accede a un servicio.
