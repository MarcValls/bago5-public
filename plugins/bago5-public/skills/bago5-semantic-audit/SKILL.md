---
name: bago5-semantic-audit
description: "Contrastar afirmaciones y comprobar contradicciones sobre modelos explícitos."
---

# Contrastar afirmaciones y comprobar contradicciones sobre modelos explícitos

Inventaría cada cita literal con su localizador. Para comparar afirmaciones, iguala referente, tiempo, ámbito, condiciones y modalidad. Revisa los supuestos y el significado de cada variable. Una repetición, una doble negación o dos redacciones distintas pueden expresar la misma proposición.

El [verificador booleano](scripts/boolean_audit.py) acepta un modelo JSON conforme al [esquema](references/input.schema.json). Ejecuta `python scripts/boolean_audit.py modelo.json` desde esta habilidad. Revisa las entradas descartadas, las tablas de verdad y los pares omitidos. El verificador opera sobre expresiones explícitas revisadas. La interpretación de lenguaje natural requiere cotejo humano con el texto original.
