# Versiones del incremento privado

## 0.4.22 · Corrección de salida y cierre de candidata

Tras publicar y releer 0.4.21, revisión de superficie CLI: el parser estándar podía
repetir argumentos inválidos. Se sustituye por error fijo INVALID_ACTION y se prueba
con datos ficticios en argumentos desconocidos y en --check=valor. No se aceptan
secretos ni se añade una vía de desbloqueo. La prueba no cambia la regla: nunca pasar
claves reales por argv, cuyo contenido es visible al sistema operativo.

38 tests: 32 core y 6 UI, con fixtures. 22 checks estáticos. Host real NO IMPLEMENTADO;
Windows/KeePassXC real NOT_RUN; uso sensible global NO_GO. Ambos manifiestos 0.4.22.
Los SHA256SUMS de evidence describen los bytes de la candidata del overlay, no una
exportación íntegra de BAGO5. Plugin Creator puede normalizar manifiestos al publicar.


## 0.4.21 · Modo privado BAGO / BAGO-PRIVATE-001 v1

Base: BAGO5 Gobernado 0.4.20, release pluginrel_6af9b485b98481918c00976085aeb16b.
Identidad conservada: plugins_6ae7ade3ef348191988cff4718deb557; USER / PRIVATE.

Añadido: skill bago5-modo-privado, contrato de host, schema sin campos sensibles,
gate SQLite cooperativo multiproceso con estados persistentes, coordinador,
lanzador KeePassXC Windows con pins y firma, UI local, pruebas y evidencias.
Actualizados: ambos manifiestos (versión/keyword; prompt sensible en manifest Codex)
y default_prompt del agente de entrada. Las instrucciones anteriores permanecen.

Conservados por overlay: .app.json, conexiones, skills anteriores, runtime opcional,
fuentes binarias, Sites, datos y permisos. No se ordena ningún borrado.
No se declara verificado el funcionamiento completo de todo BAGO5 por este incremento.

Estado: componente IMPLEMENTADO; 31 pruebas del core + 6 UI sintéticas PASS en Linux;
22 comprobaciones estáticas PASS. Windows/KeePassXC efectivo y adaptador host NOT_RUN /
NO IMPLEMENTADO. Operación sensible global NO_GO: el comportamiento actual es BLOCKED.

El ZIP de actualización es overlay, NO exportación completa instalable de BAGO5.
No reemplazar una instalación completa por los archivos de este incremento.
