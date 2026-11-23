# ALIFE-MATH-001 · Distribución y acceso · 0.1.1

## Decisión vigente del usuario

Los demás usuarios pasan por el control comercial Alife. Separar motor, MCP y política comercial significa separación de responsabilidades, no un acceso libre a los verificadores.

Cliente ChatGPT/Codex → MCP autenticado Alife → identidad + vínculo vigente + capacidad habilitada + cuota/consumo → kernel privado → resultado y recibo. Una página web futura usa la misma frontera. No hay una API secundaria sin comprobación.

El plugin es cliente y procedimiento, no servidor. El kernel, catálogo operativo, código SymPy, verificadores y adaptadores de autoridad se mantienen en el despliegue privado. No se distribuyen scripts de cálculo ni `--development-stdio` con el plugin. Las fórmulas y servicios no se activan por el mero hecho de instalarlo.

No se concede una exención implícita a `owner`, un correo o un parámetro del modelo. Una concesión de desarrollo o acceso gratuito, si se incorpora, deberá emitirse por la autoridad Alife y pasar por el mismo control; no se ha implementado una excepción aquí. El trabajo local del desarrollador es un entorno de pruebas separado, no la oferta de terceros.

## Fronteras de datos

Memoria Viva conserva contenido e historial canónicos. El enlace a Alife no concede acceso a un recuerdo. La operación matemática recibe solo contenido autorizado para procesar; no busca ni escribe en memorias. El plan concede una capacidad comercial, no propiedad sobre datos.

Los recibos de servicio conservan metadatos mínimos, nunca tokens, prompts ni expresiones. Los hashes del modelo en resultados son datos que deben clasificarse antes de subirlos a GitHub; no se publican automáticamente.

## Límite de la entrega

Hay implementación privada con pruebas de núcleo y gate con backends sintéticos. No hay backend real de identidad/vinculación/entitlements/quota/auditoría conectado, ni endpoint MCP publicado. Ante falta de autoridad el servidor falla cerrado. Las pruebas no acreditan OAuth, cobros, aislamiento real de usuarios o ejecución desde el host final.

Se reutiliza el parser booleano de auditoría semántica BAGO5 sin modificar la skill antigua. SymPy cubre operaciones algebraicas acotadas. LSI/MAT/VAC proceden de los resúmenes versionados recuperados y de esta conversación; no se presentan como documentos originales íntegros. Su evaluación de efectividad lingüística sigue NOT_RUN.
