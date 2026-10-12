# Configuración del entorno. Es el único archivo que hace falta tocar para adaptarlo.
[entorno]
nombre = "{{nombre}}"
origen = "meta-harness {{version_origen}}"
generado = "{{fecha}}"
modulos = [{{modulos_toml}}]
agentes = [{{agentes_toml}}]

[documentacion]
# Carpetas donde se busca primero (relativas a la raíz de este repo).
rutas = ["docs", "knowledge"]

[gate]
# Comandos de la compuerta, en orden; cada uno se ejecuta sin shell. Ejemplo: ["npm", "test"].
comandos = []
# Si es true, el hook impide `git commit` mientras la compuerta no haya pasado en la última hora.
bloquear_commit = false

[autoguardado]
# Commit local automático al cerrar la sesión (solo si el escaneo de secretos pasa).
commit = true
# Subir al remoto. Desactivado a propósito: actívalo cuando confíes en tu escaneo.
subir = false
rama = "main"
