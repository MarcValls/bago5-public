# Uso del ayudante booleano

Python 3.9+, solo biblioteca estándar. Entrada JSON, salida JSON por stdout; no modifica fuentes. El parámetro nombra un archivo que el usuario o el agente preparan con la formalización revisable. El JSON no puede indicar instrucciones de ejecución.

Ejemplo:

```json
{
  "claims": [
    {"source":"contrato.md:12","quote":"El modo está activo.","context":{"project":"demo","referent":"modo","time":"ahora","condition":"incondicional","modality":"hecho","scope":"misma versión"},"atoms":{"p":"El modo está activo, como bool puro y estable"},"expression":"p","mapping":"reviewed","assumptions":["Mismo instante y referente"]},
    {"source":"contrato.md:18","quote":"El modo no está activo.","context":{"project":"demo","referent":"modo","time":"ahora","condition":"incondicional","modality":"hecho","scope":"misma versión"},"atoms":{"p":"El modo está activo, como bool puro y estable"},"expression":"not p","mapping":"reviewed","assumptions":["Mismo instante y referente"]}
  ]
}
```

`mapping=reviewed` es una declaración del preparador, no una certificación automática. `mapping=candidate` conserva la ocurrencia y la excluye de pruebas lógicas. `atoms` define todas y solo las variables de la expresión. Contextos incompletos, vocabularios diferentes o conjuntos de supuestos distintos no se comparan. Para comparar dos fórmulas de vocabulario distinto, alinear explícitamente sus significados en la preparación; el script nunca adivina esa equivalencia. El contexto requiere project, referent, time, condition, modality y scope no vacíos. Es posible incluir campos extra, que también deben coincidir.

Límites: entrada de 1 MiB; 100 afirmaciones; 512 caracteres y 128 nodos AST por fórmula; 10 variables por grupo de vocabulario idéntico; 1000 pares por informe. Excesos globales: error y salida 2. Casos individuales no soportados y límite de pares: cobertura PARTIAL; salida 0 indica informe producido, no corpus correcto. Resultado `COMPLETE_FOR_ACCEPTED_BOOLEAN_MODELS` solo cubre las formalizaciones aceptadas. Siempre declarar lenguaje natural y runtime NO_COMPROBADO/NOT_RUN según corresponda.

El informe contiene inventario de fragmentos con IDs por índice, SHA del fragmento original y normalizado, grupos textuales, hallazgos lógicos y testigos. La tabla de verdad de cada grupo permite revisar exhaustividad sin ejecutar las fuentes. Una pareja compatible recibe un testigo; una diferencia recibe un contraejemplo de equivalencia. Se comprueba además la conjunción del grupo, que puede ser inconsistente sin pares contradictorios. No se afirma obtener un núcleo inconsistente mínimo. Tautologías y equivalencias son propiedades, no defectos automáticos.

Revisar el informe contra los originales conforme a SKILL.md; los hashes son de los fragmentos de entrada, NO de los archivos completos. La formalización puede omitir hechos o modelar mal las fuentes. El script no identifica errores arbitrarios en prosa o código por sí solo.

Esquema estructural: [input.schema.json](input.schema.json). El script comprueba además restricciones semánticas del modelo (átomos, AST, contexto y límites); no depende de jsonschema. Ejemplo ejecutable: `python <ruta_skill>/scripts/boolean_audit.py <ruta_skill>/examples/contradiccion.json`. Es una demostración sintética, no evidencia de una contradicción en un proyecto real.
