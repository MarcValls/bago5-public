# Errores comunes de BAGO

## Se audita la copia equivocada

Síntoma: una ruta pasa tests pero el comando `bago` ejecuta otra implementación.

Localizar y comparar:

```text
python scripts/bago_paths.py
python scripts/compare_copies.py --source <SOURCE> --runtime <RUNTIME>
```

Fuente, runtime y estado de usuario son roles distintos.

## El layout no coincide con lo esperado

El motor puede estar en la raíz, bajo `backend/` o detrás de entrypoints heredados. Detectar capacidades antes de formar comandos o rutas. La UI editable y el artefacto servido también pueden vivir separados.

## El validador pasa pero la suite falla

Clasificar antes de reparar:

- tests que buscan fuentes, Git o CI no incluidos en el runtime: contrato de empaquetado o de test;
- fallos en sesión, REPL, API, providers o persistencia: posible regresión funcional;
- dependencia externa ausente: limitación ambiental.

No sumar categorías distintas como una sola avería.

## La versión coincide pero los hashes difieren

La versión no prueba igualdad. Comparar los archivos críticos existentes en ambos layouts. En instalaciones actuales suelen incluir sesión, REPL, API, CLI, launchers y el artefacto UI.

Portar hotfixes a la fuente con tests antes de reconstruir el runtime.

## El chat rechaza el directorio

El gestor de sesión puede exigir que la raíz exista y tenga identidad de proyecto. No usar el perfil completo, la raíz de una unidad ni una ruta no autorizada como proyecto.

## El escáner marca tokens de tests

Fixtures con nombres como `LEAK-CANARY` pueden ser pruebas adversariales. Confirmar contexto antes de tratarlos como credenciales y ajustar el gate para distinguir tests de secretos reales.

## PowerShell informa `Variable reference is not valid`

Dentro de strings dobles, `$VAR:` puede requerir `$($VAR):`. No modificar scopes válidos como `$env:PATH`. Usar el reparador primero sin `--apply`.

## No hay providers cloud

No es fallo si son opcionales y faltan credenciales. Exigir al menos un provider sano y verificar que la sesión no hereda silenciosamente un proveedor anterior.

## El estado no es escribible

Mantener estado mutable fuera de runtimes protegidos. Resolver la ruta de estado desde configuración y roles; no asumir una ubicación fija.
