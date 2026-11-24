# Misión cognitiva integrada — BAGO5os 1.4.3

Este módulo conserva la composición SessionManager → ContextStore → interpretación reflexiva
→ admisión SPBE → razonador del host → PlanEngine → doce etapas Spiral → autorización/gateway
→ observación → reflexión → LearningWriter/memoria → proceso siguiente.
No es otro coordinador: las ejecuciones y el cierre se admiten mediante `suite_control`.

## Dos comprobaciones distintas
- `cognitive config-check --output RUTA_NUEVA`: importa el módulo de configuración instalado,
  comprueba 12 criterios en procesos nuevos y consume la configuración mediante SessionManager.
- `cognitive replay --output RUTA_NUEVA`: ejecuta la composición sobre una copia histórica del
  defecto de RC2, utilizando las seis respuestas grabadas en COG-REPAIR-002. Se espera
  5/12 → 12/12 → 12/12. El runtime ejecutor es 1.4.3; el defecto observado es la fixture antigua.

Ambos se invocan con `python -B scripts/suite_orchestrator.py` desde la instalación.
Las salidas siempre se crean fuera del payload. No se necesitan los ZIP históricos para arrancar.

## LIVE, con un razonador real del host
Desde la instalación:

```sh
python -B scripts/suite_orchestrator.py cognitive init --output /ruta/datos/mision-live
python -B scripts/suite_orchestrator.py cognitive cycle --work /ruta/datos/mision-live --number 1
```

El ciclo espera una solicitud en `mailbox/cycle01-propose-01.request.json`. El host debe leer
`system` y todos los mensajes y emitir una decisión nueva conforme al contrato. No sustituirla
por el banco de grabaciones. Entregarla desde otra terminal:

```sh
python -B scripts/suite_orchestrator.py cognitive deliver --work /ruta/datos/mision-live --request cycle01-propose-01 --content /ruta/respuesta-actual.json --author "Identidad del host real"
```

Leer la observación nueva de REFLECT y responder a esa solicitud. Después:

```sh
python -B scripts/suite_orchestrator.py cognitive consume --work /ruta/datos/mision-live --check cycle1
```

Repetir para ciclos 2 y 3, consumiendo cada entrega; luego ejecutar `cognitive verify`,
`cognitive consume --check final-verification` y `cognitive close` con el mismo `--work`.
El modo LIVE tiene límites de espera; no continúa inventando respuestas si falta el host.

Para detener: `cognitive stop --work RUTA --reason "Parada explícita"`. Solo una instrucción
`cognitive resume --work RUTA --reason "Reanudación explícita"` permite admitir trabajo nuevo.
Una parada no revierte efectos ya producidos ni certifica la cancelación de un host externo.

## Estado y confianza
La conexión de contexto procede de COG-REPAIR-002. Mantiene la instrucción de misión sometida
al clasificador y liga las observaciones como datos, no autorizaciones. Esto no demuestra
inmunidad general a prompt injection. Los permisos son de un uso, emitidos por un host local
confiable: no es autenticación externa ni sandbox del sistema operativo.

SPBE→PEC sigue sin enlace nativo. La ejecución usa el puente explícito PlanEngine/Gateway.
Aprendizaje, transferencia y ventaja de utilidad no se evalúan aquí. No inferir autonomía
sin host ni atribuir razonamiento nuevo a una reproducción de respuestas históricas.

Los contratos de las grabaciones no incluyen razonamiento privado: son decisiones, hechos,
riesgos, acciones y resúmenes de reflexión. Las grabaciones y la fixture conservan su procedencia.
