# Integración ZIP Auditor 0.3.0 en BAGO5os 1.4.7 RC2

Distribución **derivada FIX02**: identidad propia `CONTEXT-LIFECYCLE-NATIVE-RC2-ZIPA-FUSION-P1-FIX02`.
Deriva de la integración ZIPA 01 (`CONTEXT-LIFECYCLE-NATIVE-RC2-ZIPA-INTEGRATION-01`); no es el RC2 original: los archivos del router, la identidad, SKILL.md, y dos
funciones de salida del auditor han cambiado, y se han añadido código y Python privado.

- Motor y los siete componentes de análisis originales conservados, excepto `un_clic.py`
  (para permitir directorio de informes externo). El comprobador `VERIFICAR_PACK.py`
  verifica los archivos declarados en `SHA256SUMS.json`, actualizado para el único
  archivo que ha cambiado; sin esa actualización no debe declararse PASS.
- La consola `control/terminal.py` solo cambia la ubicación de informes si el puente
  `suite_zip_auditor.py` establece la variable `BAGO_ZIPA_REPORTS_DIR`.
- El EXE de instalación verifica hashes antes/después de la instalación, prepara una
  carpeta temporal, y en actualizaciones conserva backup sin destruir la anterior.
- El programa `BAGO5os.exe` lanza Python privado y ofrece panel de operaciones.
- No instala hooks, modifica configuraciones de Codex ni activa procesos de fondo.
- Python Windows incluido 3.13.16, PSF License; Go license ver fuentes.
**P1-FIX02 candidato:** las coincidencias exclusivas de nombres genéricos de raíz
(`README.md`, `package.json`, etc.), con bytes diferentes y sin ningún hash
compartido, ya no generan una propuesta de fusión. El informe diferencia las
parejas descartadas como señal de fusión. No resuelve equivalencia semántica:
colisiones reales o componentes compartidos siguen requiriendo revisión.

## Validación

Windows 10/11 real (doble clic, teclado, AV/SmartScreen, permisos): **NOT_RUN** en
el entorno Linux de generación. Los tests realizados se adjuntan al paquete.
