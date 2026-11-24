# COG-REPAIR-002 — Preservar una configuración elegida explícitamente

Objetivo autorizado en esta copia de trabajo: guardar mediante la API pública de ConfigManager un proveedor y modelo elegidos, y recuperarlos sin sustituciones silenciosas en un proceso posterior. El consumidor SessionManager debe observar esa configuración persistida; no se afirma que cambiar config seleccione por sí solo el proveedor de inferencia de una sesión ya creada.

## Frontera
config_manager.py es una copia byte a byte del componente real de BAGO5os 1.4.2 RC2; consultar PROVENANCE.json. No es un defecto inyectado en una app sintética. El parche solo puede cambiar ese archivo de la copia. Las dependencias y consumidores se cargan de la Suite original en procesos aislados. El motor que conduce la misión permanece intacto.

## Decisión de compatibilidad explícita
Los valores por defecto nuevos (ollama-cloud y deepseek-v3.1:671b) se conservan cuando falta configuración o el usuario pide reset. Guardar explícitamente ollama-local o llama3.2:3b NO autoriza sustituirlos al cargar. No debe inferirse una migración solo a partir del nombre del proveedor/modelo. Se reconoce el cambio respecto a la coerción heredada: las configuraciones antiguas explícitas se conservan. No se introduce un migrador nuevo en esta reparación.

## Aceptación fija
C01 proveedor local por set, C02 modelo por set, C03 setters de propiedades, C04 otras elecciones, C05 defaults en instalación nueva, C06 configuración parcial, C07 opciones ajenas, C08 cargas repetidas sin cambios, C09 reset explícito, C10 aislamiento de raíces, C11 carga por SessionManager y C12 rebind por SessionManager.

El observador ejecuta esos casos en procesos distintos, sobre datos temporales. FAIL del producto es diagnóstico válido; no equivale a fallo del proceso observador. Antes de editar hace falta observar FAIL. Tras corregir se repiten los criterios y, en otro ciclo/proceso, se recupera memoria y se verifica sin reaplicar el parche.

## Fuera de alcance
No se certifican un modelo o servicio Ollama, inferencia local/nube, UI, ADL, Windows, bloqueo de concurrencia, migración universal, aprendizaje o SPBE→PEC. No cambiar defaults globales ni credenciales. No modificar los originales, otras candidatas ni instalaciones activas.
