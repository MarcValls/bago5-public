# Uso de esta actualización

Invocación: `$bago5-matematicas` desde el plugin BAGO5 Gobernado. Sirve para coordinar el recorrido de formalización matemática y las futuras llamadas protegidas de Alife.

Esta actualización es un cliente. No contiene el motor matemático ni registra un endpoint remoto inventado. Sin herramientas Alife autenticadas el cálculo del servicio queda `ALIFE_SERVICE_NOT_CONNECTED`, no se simula. La lectura habitual de Memoria Viva y el resto del plugin permanecen disponibles conforme a sus permisos existentes.

El motor y su gate están en un paquete privado separado para el propietario/desplegador. Para habilitar la oferta comercial faltan la conexión a las autoridades reales de Alife y el despliegue autenticado con prueba de terceros. No subir ese paquete servidor al plugin distribuible ni a repositorios públicos.

No es necesario crear un segundo Site para desarrollar la lógica. Si se añade una página al Site Alife, consumirá el mismo backend protegido; no será un sustituto de autenticación o suscripción.
