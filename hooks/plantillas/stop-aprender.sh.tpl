#!/usr/bin/env bash
# Hook de fin de sesión (plantilla): el harness aprende de las fuentes registradas y se sincroniza.
# <!-- tipo: herramienta · capa: 4 -->
#
# 1) aprender: corre `harness-aprender.py escanear` en silencio y con límite de frecuencia. Solo LEE las fuentes y solo escribe
#    en la cola local (fuera de los repositorios).
# 2) sincronizar: `harness-sincronizar.py` hace commit, trae lo remoto y sube SOLO la rama main, y únicamente si pasa la compuerta de
#    publicación (verificar.sh + escaneo de secretos, personas y términos prohibidos). Si algo falla no sube nada y lo avisa.
# Ninguno de los dos hace fallar la sesión (siempre sale con 0). Para solo probar la compuerta: harness-sincronizar.py --solo-compuerta.
# Cómo se instala: copiar este archivo (sin .tpl) a la carpeta de hooks del agente, sustituir __HARNESS_RAIZ__ por la ruta del
# repositorio del harness y registrarlo como hook de fin de sesión.
HARNESS="${HARNESS_RAIZ:-__HARNESS_RAIZ__}"
[ -d "$HARNESS/herramientas" ] || exit 0
python3 "$HARNESS/herramientas/harness-aprender.py" escanear --silencioso --max-frecuencia "${HARNESS_APRENDER_CADA:-1800}" >/dev/null 2>&1 || true
if [ "${HARNESS_SINCRONIZAR:-1}" = "1" ]; then
  python3 "$HARNESS/herramientas/harness-sincronizar.py" --silencioso 2>/dev/null || true
fi
exit 0
