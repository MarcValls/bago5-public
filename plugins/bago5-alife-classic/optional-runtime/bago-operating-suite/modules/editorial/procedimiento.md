# Editorial IALP — especialista subordinado

El Operating Layer sigue siendo el orquestador único y dueño de autoridad, contexto,
alcance, BAGO-CDP-001 y cierre de la tarea. Este módulo genera y comprueba documentos;
no decide la verificación funcional de una aplicación ni activa otros especialistas.

## Activación y responsabilidades

Activar para `$bago-pdf`, IALP, maquetación, PDF o manuales. La auditoría visual de un
PDF no activa por sí sola frontend, BPBR ni el paquete de auditoría arquitectónica.
Cuando la solicitud los nombra explícitamente, combinar solo esos especialistas.
`plan` es clasificación y propuesta, no ejecución ni concesión de acceso.

Antes de ejecutar: fuente concreta autorizada, recursos en su carpeta, destino nuevo
fuera de la fuente y de la Suite, entorno editorial identificado. No renderizar
material no confiable como si el subproceso fuese un sandbox de sistema operativo.
No se instala software ni se solicitan servicios externos automáticamente.

## Contrato operativo

- `doctor`: inspecciona dependencias en el intérprete seleccionado. Informa versiones
  diferentes al lock, herramientas ausentes y carga nativa de WeasyPrint. PASS solo
  significa que están presentes las dependencias Python básicas, no que cualquier
  diagrama pueda renderizarse. Mermaid y DOT necesitan sus ejecutables.
- `export-kit`: extrae el runtime identificado en una carpeta nueva para preparar
  dependencias externas. No ejecuta el kit ni instala nada.
- `preflight`: inspección de un MD, sin editarlo. REVIEW se traduce a INCONCLUSIVE.
- `build`: fuente preservada por defecto, motor WeasyPrint, vistas de todas las páginas,
  informe, hashes y borrador. Se contrastan inventario, auditoría y vistas. Nunca
  convierte la generación en una revisión visual.
- `record-review`: registra una declaración explícita del revisor en una copia nueva
  del borrador; exige páginas, veredicto y checklist. No inventar inspecciones ni
  atribuir al usuario una revisión realizada por un agente.
- `validate-review`: revalida sin escribir la correspondencia entre recibo y archivos.
- `close`: copia a un destino nuevo y exige revisión vigente y controles superados.
  Un fallo bloquea el cierre. No sobrescribe entregas previas.
- `test`: pruebas upstream en una carpeta temporal, con logs en un destino nuevo.
  Incluyen mocks y no equivalen a validar todas las herramientas externas.

Ejemplo desde la raíz de la skill instalada:

```text
python -B scripts/suite_orchestrator.py verify --modules editorial
python -B scripts/suite_orchestrator.py plan --task '$bago-pdf'
python -B scripts/suite_orchestrator.py editorial doctor --python C:\BAGO-ENV\editorial\Scripts\python.exe
```

El parámetro `--python` permite mantener las dependencias fuera del núcleo. El router
usa biblioteca estándar; el proceso editorial usa Python aislado `-I -B`, runtime
fijado, argumentos estructurados y límite de tiempo. Esto NO proporciona aislamiento
OS/red. En Windows no se ha probado la terminación de procesos descendientes.

## Conservación y trazabilidad

El código Python upstream está conservado byte a byte. El ZIP operativo es una
**derivación explícita**, no el ZIP original completo: incluye código, contratos,
CSS, plantillas, configuración y tests. Omite archivos tipográficos y salidas
históricas. La adaptación CSS resuelve fuentes por nombre local; puede variar la
paginación entre equipos. Revisión obligatoria en el entorno de destino.

El ZIP contiene SOURCE_DERIVATION.json, UPSTREAM_MANIFEST.json y SHA256SUMS.txt.
La procedencia se fija en el [lock de fuentes](../../integrations/source-packs/SOURCE_PACKS_LOCK.json).
No declarar una reproducción exacta de dependencias cuando `exact_dependency_lock`
es falso. La evidencia histórica del kit no se convierte en evidencia nueva.

El [worker](worker.py) solo se usa a través del router. La [fuente sintética](fixtures/SMOKE.md)
permite una demostración independiente sin rehacer el manual de producción.
