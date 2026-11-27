# Flujo abstracto de orquestación BAGO

## 1. Entrada

Resolver qué launcher y entrypoint ejecuta realmente el usuario. Validar versión y ayuda solo si la superficie los ofrece.

## 2. Proyecto, sesión y estado

Localizar el componente que posee:

- raíz autorizada;
- sesión activa;
- provider y modelo;
- persistencia;
- workspace operativo.

No atribuir autoridad a la UI.

## 3. Chat o REPL

Comprobar qué gestor de sesión instancia y si comparte el mismo contrato que CLI y manager. Un hotfix exclusivo del runtime crea deriva aunque la versión coincida.

## 4. Comandos

Consultar primero catálogo o ayuda. Probar comandos headless y de diagnóstico únicamente cuando estén anunciados. Catálogo visible y registro ejecutable deben coincidir.

## 5. Providers y routing

Separar provider instalado, configurado y sano. Los providers opcionales pueden faltar; debe existir una ruta operativa y la elección de sesión no debe heredar silenciosamente otra configuración.

## 6. API y clientes

El backend conserva autoridad. Detectar por separado:

- fuente del cliente;
- artefacto compilado;
- artefacto servido;
- bridge o API que transporta estado.

Validar sus contratos sin exigir fuentes que la distribución haya decidido excluir.

## 7. Cierre

Considerar cerrado el flujo solo si:

1. fuente, runtime y estado están identificados;
2. validadores disponibles pasan;
3. pruebas funcionales pasan;
4. ruido de empaquetado está clasificado;
5. divergencias críticas están resueltas o explicadas;
6. el runtime puede reconstruirse desde la fuente que conserva la reparación.
