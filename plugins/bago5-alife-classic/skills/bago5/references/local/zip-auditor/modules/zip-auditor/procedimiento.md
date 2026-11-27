# ZIP Auditor · especialista integrado en BAGO5os

**Ámbito autorizado:** abrir ZIP como datos y crear reportes estáticos. Nunca ejecutar contenido del ZIP. Para copiar ZIP completos a grupos propuestos hace falta aceptación explícita, separada del análisis.

## Ejecución

- En la interfaz `BAGO5os.exe`, seleccionar **ZIP Auditor** para el menú de selección de carpetas.
- `python -B scripts/suite_orchestrator.py zip-auditor --analizar "C:\\Mis ZIP" --no-open` crea solo informes y plan.
- `python -B scripts/suite_orchestrator.py zip-auditor --analizar "C:\\Mis ZIP" --no-open --aceptar-agrupacion` permite copiar ZIP completos por grupos, pero jamás reescribe originales.
- `python -B scripts/suite_orchestrator.py zip-auditor --verificar` valida la integridad del motor original.

Por defecto los informes se guardan fuera del directorio instalado, en `%LOCALAPPDATA%\\BAGO5os\\ZIP_AUDITOR_INFORMES`.

## Límites documentados

La inferencia de familias es heurística, no asegura equivalencia funcional. El informe de *posibles fusiones* de 0.3.0 puede marcar conflictos de rutas genéricas entre familias distintas; son diagnósticos, no fusiones aprobadas. No se ejecutan programas de los ZIP. Los anidados no se analizan en profundidad; hay límites de tamaño/lectura. STOP y permisos de BAGO5os mantienen prioridad; no se activan agentes de manera automática.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
