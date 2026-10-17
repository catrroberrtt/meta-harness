#!/usr/bin/env bash
# Hook de inicio de sesión (plantilla): avisa cuánto conocimiento NUEVO hay sin digerir, a partir de un archivo de novedades.
# <!-- tipo: herramienta · capa: 4 -->
#
# Qué resuelve: lo nuevo que existe en las fuentes (código, documentación, tickets) y todavía no está en la base de conocimiento no
# se ve solo; si nadie lo mira, se concluye «no está documentado» sin haberlo buscado. Este aviso hace que su existencia aparezca
# sola al abrir la sesión, sin depender de que el agente se acuerde de mirar. Solo imprime texto: no ejecuta nada más.
#
# Contrato del archivo de novedades (lo genera un proceso periódico de la instancia; este hook solo lo lee): Markdown con secciones
# `## <título>` y, dentro de cada una, una viñeta `- ` por pendiente. El aviso cuenta las viñetas por sección y avisa si el archivo
# lleva más de HARNESS_NOVEDADES_MAX_HORAS (36 por defecto) sin actualizarse, señal de que el proceso periódico no corrió.
# Cómo se instala: copiar este archivo (sin .tpl) a la carpeta de hooks del agente, sustituir __NOVEDADES__ por la ruta del archivo
# y registrarlo como hook de inicio de sesión (SessionStart). Si el archivo no existe, sale sin avisar y sin fallar.
N="${HARNESS_NOVEDADES:-__NOVEDADES__}"
[ -f "$N" ] || exit 0
command -v jq >/dev/null || exit 0

resumen="$(awk '/^## /{sec=substr($0,4); next} /^- /{n[sec]++} END{for (s in n) printf "%s: %d · ", s, n[s]}' "$N")"
[ -n "$resumen" ] || exit 0
edad_h=$(( ( $(date +%s) - $(stat -c %Y "$N") ) / 3600 ))

msg="ℹ Conocimiento sin digerir — ${resumen% · }. Lista completa: ${N}. Antes de decir «no está documentado» o «no existe», búscalo en las fuentes y lee la página o el archivo completo."
if [ "$edad_h" -gt "${HARNESS_NOVEDADES_MAX_HORAS:-36}" ]; then
  msg="$msg
⚠ El archivo de novedades tiene ${edad_h} h: el proceso periódico que lo actualiza no corrió."
fi
jq -n --arg msg "$msg" '{systemMessage: $msg, hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $msg}}'
exit 0
