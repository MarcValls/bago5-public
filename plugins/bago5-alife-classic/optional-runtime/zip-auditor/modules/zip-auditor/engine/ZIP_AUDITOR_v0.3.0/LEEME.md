ZIP AUDITOR 0.3.0 - AGRUPAR VERSIONES POR CONTENIDO
=================================================

INICIO
Guarda ZIP_AUDITOR_v0.3.0_PORTABLE.exe en una carpeta propia y abrelo con doble
clic. Python va incluido. El programa prepara ZIP_AUDITOR_030_DATOS junto al EXE.
Usa flechas/Enter o numeros. Elige la carpeta de tus ZIP y si incluir subcarpetas.
La distribucion ya no incorpora los ZIP de ejemplo ni la opcion de analizarlos.

PROPUESTA DE AGRUPACION
Al terminar se generan el informe y una propuesta de familias de aplicaciones.
Se compara contenido interno: codigo y textos, huellas exactas/similitud y
metadatos internos de proyecto. El nombre externo del ZIP no decide la familia.
Las dependencias empaquetadas, caches y archivos genericos no bastan para agrupar.
Cada grupo tiene un nombre automatico derivado del contenido y muestra evidencias.
Los casos sin evidencia suficiente permanecen separados para revision.
La agrupacion es una propuesta heuristica, no una certificacion de identidad ni
compatibilidad funcional de programas diferentes.

ACEPTACION Y COPIAS
Revisa los grupos y el destino antes de responder Si. Si rechazas, no se crean
carpetas agrupadas. Al aceptar se COPIAN los ZIP completos, sin extraer ni
fusionar los archivos que contienen. Los ZIP originales no se mueven ni borran.
La salida del analisis recibe una subcarpeta PAQUETES_AGRUPADOS con un directorio
por grupo. Se conservan los nombres de ZIP cuando no colisionan; en caso de
coincidencia se añade un sufijo inequívoco. La trazabilidad recoge origen y hash.
Una ejecucion nueva nunca sobrescribe una agrupacion anterior.
Antes y despues de copiar se comprueban las identidades. Si un ZIP cambia desde
el analisis, la operacion se detiene. No se publica una agrupacion parcial.

RESULTADOS
Los resultados estan junto al EXE, dentro de:
ZIP_AUDITOR_030_DATOS/ZIP_AUDITOR_v0.3.0_INFORMES
Cada analisis crea una carpeta propia. Dentro estan report.html, report.json,
los CSV y verificaciones, RESUMEN_FUSIONES.html/.json y PROPUESTA_AGRUPACION.html/.json.
Tras aceptar aparecen PAQUETES_AGRUPADOS y su manifiesto de procedencia.
El menu permite abrir la propuesta, los resultados y revisar/aplicar la ultima
agrupacion. Los informes de la version 0.2.2 anterior se conservan en su carpeta.

CLI OPCIONAL (EN LA CARPETA DEL EXE)
  .\ZIP_AUDITOR_v0.3.0_PORTABLE.exe --help
  .\ZIP_AUDITOR_v0.3.0_PORTABLE.exe --verificar
  .\ZIP_AUDITOR_v0.3.0_PORTABLE.exe --analizar "C:\Mis ZIP" --no-open
  .\ZIP_AUDITOR_v0.3.0_PORTABLE.exe --analizar "C:\Mis ZIP" --recursive --aceptar-agrupacion
Sin --aceptar-agrupacion, la CLI solo analiza y propone; no copia los paquetes.
El menu solicita una respuesta expresa antes de copiar.

INTEGRIDAD Y RECUPERACION
Se verifica el motor, la interfaz y el Python privado antes de ejecutarlos.
Una carpeta de programa alterada no se sobrescribe. Conserva la carpeta
ZIP_AUDITOR_030_DATOS con otro nombre y abre de nuevo el EXE para recuperar
una extraccion limpia. Los informes previos permanecen en la copia conservada.
No edites archivos del programa para cambiar preferencias.

ALCANCE
Aplicacion 0.3.0. El motor de inventario/dependencias 0.2.2 se reutiliza sin
modificar sus siete archivos seleccionados; se retiran ejemplos e historicos.
No se ejecutan scripts, instaladores ni programas contenidos en los ZIP de entrada.
Los miembros de ZIP anidados no se analizan de forma recursiva; se declara la
cobertura y los limites de lectura. Versiones reescritas totalmente pueden
permanecer separadas; aplicaciones derivadas de una base comun requieren revision.
Destino: Windows 10/11 x64, Python privado 3.13.16. Sin instalacion de sistema.
La compilacion/pruebas en Linux o Wine no acreditan Explorer en Windows real.
Windows real, doble clic Explorer y teclado fisico: NOT_RUN durante esta entrega.

FUENTES
control/ contiene el codigo de interfaz, propuestas y copias gobernadas por
aceptacion. FUENTES_CONTENEDOR/ conserva lanzador/constructor y pruebas.
ORIGENES.json documenta las identidades y retiradas autorizadas.
Python conserva python/LICENSE.txt y Go LICENSES/GO_LICENSE.txt.
El contenedor generado no incorpora firma de editor.
