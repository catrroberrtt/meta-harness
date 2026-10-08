#!/usr/bin/env bash
# GENERADO por instalador/generar-politicas.py a partir de una politica por proyecto.
# NO editar a mano: se edita la politica y se vuelve a generar.
# Politica de origen: @@POLITICA_ORIGEN@@
#
# PreToolUse hook (Bash): control de acceso a la base de datos.
#   - DENY duro: comandos prohibidos de la politica (migraciones, semillas, CLI del ORM...),
#     cualquier escritura/DDL fuera del ambiente de escritura declarado y cualquier conexion
#     a un host que no sea local.
#   - ALLOW: SELECT de solo lectura contra un host local; escritura solo en el ambiente
#     declarado con escritura permitida (si existe).
#   - ASK: host no resoluble (variable o sin -h), scripts que hablan con la base.
# Ningun ambiente, puerto, base ni cuenta esta escrito aqui: todo sale de la politica.
set -uo pipefail

input="$(cat)"
command="$(printf '%s' "$input" | jq -r '.tool_input.command // empty')"
[ -n "$command" ] || exit 0

root="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
name="$(basename "$root")"

# Alcance: solo los repos que la politica declara.
case "$name" in
  @@ALCANCE_CASE@@) ;;
  *) exit 0 ;;
esac

@@REMOTE_BLOCK@@

ask() {
  jq -n --arg reason "@@ETIQUETA@@ en '$name': $1" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $reason}}'
  exit 0
}

deny() {
  jq -n --arg reason "Bloqueado por @@ETIQUETA@@ en '$name': $1. Entrega el comando/SQL al usuario para que lo corra el." \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  exit 0
}

allow() {
  jq -n --arg reason "@@ETIQUETA@@ en '$name': $1" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "allow", permissionDecisionReason: $reason}}'
  exit 0
}

# --- Ambiente de escritura del agente (solo si la politica declara uno) ------------------
# Vale unicamente si el archivo de entorno del repo apunta a ese ambiente; para el cliente SQL
# ademas el comando debe nombrar esa base, no nombrar otra conocida y no usar otro puerto.
AGENTE_HABILITADO=@@AGENTE_HABILITADO@@

env_es_ambiente_agente() {
  [ "$AGENTE_HABILITADO" = "1" ] || return 1
  local f="$root/@@ARCHIVO_ENV@@" h p d
  [ -f "$f" ] || return 1
  h="$(grep -E '^@@VAR_HOST@@=' "$f" | tail -n1 | cut -d= -f2- | tr -d '"'"'"' \r')"
  p="$(grep -E '^@@VAR_PUERTO@@=' "$f" | tail -n1 | cut -d= -f2- | tr -d '"'"'"' \r')"
  d="$(grep -E '^@@VAR_BASE@@=' "$f" | tail -n1 | cut -d= -f2- | tr -d '"'"'"' \r')"
@@AGENTE_ENV_CHECKS@@
}

cliente_apunta_al_ambiente_agente() {
  env_es_ambiente_agente || return 1
  printf '%s' "$comando_ejecutable" | grep -qE @@AGENTE_BASE_REGEX@@ || return 1
@@BASES_AJENAS_CHECK@@
  printf '%s' "$comando_ejecutable" | grep -qiE '\b(drop|create)[[:space:]]+(database|schema)\b' && return 1
  local port
  port="$(printf '%s' "$comando_ejecutable" | grep -oE -- '(^|[[:space:]])(-P|--port)[[:space:]=]*[^[:space:];|&]+' | tail -n1 | sed -E 's/^[[:space:]]*(-P|--port)[[:space:]=]*//' | tr -d '\042\047')"
  case "$port" in @@PUERTO_CMD_CASE@@) return 0 ;; *) return 1 ;; esac
}

# --- Autorizacion explicita de la lectura ------------------------------------------------
# ESTRICTA: falla hacia "sin decision" (= pregunta), nunca hacia allow. Solo si TODOS los
# tramos del comando son conocidos e inocuos y el SQL es de lectura.
#   $1 = cliente | motor ; el comando llega por CMD_ANALIZAR. rc 0 = inocuo.
solo_lectura_estricta() {
  CMD_ANALIZAR="$comando_ejecutable" python3 - "$1" <<'PY'
import os, re, sys
modo = sys.argv[1]
cmd = re.sub(r"\\\n", " ", os.environ["CMD_ANALIZAR"])          # continuaciones de linea
if re.search(r"`|\$\(|<\(|>\(|<<", cmd):                        # sustituciones / heredocs: no se analizan
    sys.exit(1)
tramos = [t.strip() for t in re.split(r"&&|\|\||;|\||\n", cmd) if t.strip()]
if not tramos:
    sys.exit(1)
Q = r"""(?:"[^"$`\\]*"|'[^'\\]*'|[\w./,:=@%+-]+)"""             # argumento simple, sin expansiones
CD = re.compile(r"^cd\s+" + Q + r"$")
SET = re.compile(r"^set\s+[-+]a$")
ENV = re.compile(r"^(?:\.|source)\s+\./@@ARCHIVO_ENV_RE@@(?:\s*>\s*/dev/null)?(?:\s*2>&1)?$")
MOTOR = re.compile(r"^(?:ba)?sh\s+(?:\S*/)?(?:@@MOTOR_RE@@)(?:\s+" + Q + r")*$")
CLI = re.compile(r"^(?:MYSQL_PWD=\"\$@@VAR_CONTRASENA@@\"\s+)?mysql\s+.*$", re.S)
SOLO_SELECT = re.compile(r"^\s*(?:select|with|show|describe|desc|explain)\b", re.I)
PROHIBIDO = re.compile(r"\b(?:into\s+(?:outfile|dumpfile)|load_file|for\s+update|lock\s+in\s+share\s+mode|sleep\s*\(|benchmark\s*\(|call|execute)\b", re.I)
sql_fuentes, n_cli, n_motor = [], 0, 0
for t in tramos:
    if CD.match(t) or SET.match(t) or ENV.match(t):
        continue
    if modo == "motor" and MOTOR.match(t):
        n_motor += 1
        continue
    if modo == "cliente" and CLI.match(t):
        sin_comillas = re.sub(r'"[^"]*"|\'[^\']*\'', '""', t)      # un `>` dentro del SQL no es redireccion
        if re.search(r">(?!\s*/dev/null)(?!&)", sin_comillas):
            sys.exit(1)
        n_cli += 1
        for m in re.finditer(r"""(?:-e|--execute)[ =]*(?:"([^"]*)"|'([^']*)')""", t):
            sql_fuentes.append(m.group(1) or m.group(2))
        for m in re.finditer(r"<\s*([^\s;|&<>]+\.sql)\b", t):
            if not os.path.isfile(m.group(1)):
                sys.exit(1)
            sql_fuentes.append(open(m.group(1), encoding="utf-8", errors="ignore").read())
        continue
    sys.exit(1)                                                   # cualquier otro tramo: no se autoriza
if modo == "motor":
    sys.exit(0 if n_motor == 1 else 1)                            # exactamente UN motor
if n_cli != 1 or not sql_fuentes:
    sys.exit(1)
for sql in sql_fuentes:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    sql = re.sub(r"(?m)(--|#)[^\n]*", " ", sql)
    for st in [s for s in sql.split(";") if s.strip()]:
        if not SOLO_SELECT.match(st) or PROHIBIDO.search(st):
            sys.exit(1)
sys.exit(0)
PY
}

# --- Separar el comando real del contenido que solo se escribe a un archivo -------------
# El cuerpo de un heredoc se descarta SOLO si la linea que lo abre redirige a un archivo y no
# invoca un cliente SQL. Un heredoc que alimenta al cliente se conserva entero.
comando_ejecutable="$(printf '%s' "$command" | awk '
  BEGIN { saltando = 0 }
  saltando == 1 {
    if ($0 == delim) { saltando = 0 }
    next
  }
  {
    print
    if (match($0, /<<-?[\047"]?[A-Za-z_][A-Za-z0-9_]*[\047"]?/)) {
      abre = $0
      invoca_cliente = (abre ~ /(@@CLIENTES_AWK@@)/)
      redirige_a_archivo = (abre ~ />[[:space:]]*[^&[:space:]]/)
      if (redirige_a_archivo && !invoca_cliente) {
        delim = substr($0, RSTART, RLENGTH)
        gsub(/^<<-?[\047"]?|[\047"]?$/, "", delim)
        saltando = 1
      }
    }
  }
')"

# --- Descartar los tramos que solo LEEN texto -------------------------------------------
# Se descarta el tramo, no el comando. El filtro vive junto a este hook.
dir_hook="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
comando_ejecutable="$(printf '%s' "$comando_ejecutable" | python3 "$dir_hook/filtrar-tramos-de-lectura.py" 2>/dev/null || printf '%s' "$comando_ejecutable")"

# --- Comandos prohibidos por la politica ------------------------------------------------
@@COMANDOS_BLOCK@@

# --- Scripts que hablan con la base -----------------------------------------------------
# No se intenta analizar bash: se mira si el archivo invocado menciona un cliente y se decide.
# Cualquier script que mencione un cliente -> ASK (lo decide el usuario).
for script in $(printf '%s' "$comando_ejecutable" \
    | grep -oE -- '(^|[[:space:]])(\./|(ba|z|da)?sh[[:space:]]+)[^[:space:];|&<>]+\.sh' \
    | sed -E 's/^[[:space:]]*((ba|z|da)?sh[[:space:]]+|\.\/)//'); do
  ruta="$script"
  [ -f "$ruta" ] || ruta="$PWD/$script"
  [ -f "$ruta" ] || continue
  ruta="$(cd "$(dirname "$ruta")" 2>/dev/null && pwd)/$(basename "$ruta")"
  grep -qE '(^|[;&|(]|[[:space:]])(@@CLIENTES_RE@@)([[:space:]]|$)' "$ruta" || continue

  nombre="$(basename "$ruta")"
@@SCRIPTS_BLOCK@@
  # Motores de solo lectura: se autorizan SOLO si su contenido es el que se reviso (sha256
  # fijado por el usuario en el archivo de la politica). Editar el motor cambia el hash.
  pin="@@PIN_PATH@@"
  hash="$(sha256sum "$ruta" 2>/dev/null | cut -d' ' -f1)"
  if [ -n "$pin" ] && [ -n "$hash" ] && [ -f "$pin" ] && grep -q "^$hash " "$pin" && solo_lectura_estricta motor; then
    allow "motor de solo lectura '$nombre' (contenido fijado por sha256): autorizado sin preguntar"
  fi
  ask "el script '$nombre' habla con la base y no se puede resolver leyendolo que hace. Revisalo antes de aprobar."
done

# --- Cliente SQL directo ----------------------------------------------------------------
# El nombre del cliente tiene que aparecer como TOKEN en posicion de comando, no dentro de una
# ruta.
printf '%s' "$comando_ejecutable" \
  | grep -qE '(^|[;&|(]|[[:space:]])(@@CLIENTES_RE@@)([[:space:]]|$)' || exit 0

host_pre="$(printf '%s' "$comando_ejecutable" \
  | grep -oE -- '(^|[[:space:]])(--host|-h)[[:space:]=]*[^[:space:];|&]+' \
  | tail -n1 \
  | sed -E 's/^[[:space:]]*(--host|-h)[[:space:]=]*//' \
  | tr -d '\042\047')"
agente_en_ambiente=0
case "$host_pre" in
  @@HOSTS_AGENTE_CASE@@) cliente_apunta_al_ambiente_agente && agente_en_ambiente=1 ;;
esac

# Escritura / DDL escrita en el propio comando.
if printf '%s' "$comando_ejecutable" | grep -qiE '\b(insert|update|delete|drop|alter|truncate|rename|grant|revoke|create[[:space:]]+(table|view|index|database|procedure|function|trigger))\b'; then
  if [ "$agente_en_ambiente" = "1" ]; then
    allow "escritura/DDL contra @@AGENTE_ETIQUETA@@"
  fi
  deny "es una escritura/DDL contra la base -- @@LECTURA_RESUMEN@@"
fi

# Escritura / DDL escondida en un archivo que se le pasa al cliente (por '<' o canalizado).
for archivo_sql in $(printf '%s' "$comando_ejecutable" \
    | grep -oE -- '(<[[:space:]]*|[[:space:]])[^[:space:];|&<>]+\.(sql|SQL|ddl|dump)' \
    | sed -E 's/^(<[[:space:]]*|[[:space:]])//'); do
  [ -f "$archivo_sql" ] || continue
  if grep -qiE '\b(insert|update|delete|drop|alter|truncate|rename|grant|revoke|create[[:space:]]+(table|view|index|database|procedure|function|trigger))\b' "$archivo_sql"; then
    [ "$agente_en_ambiente" = "1" ] && allow "archivo SQL con escritura contra @@AGENTE_ETIQUETA@@"
    deny "le pasa al cliente el archivo '$archivo_sql', que contiene una escritura/DDL"
  fi
done

# Host: solo cuando -h/--host aparece como flag real (frontera antes del flag, para no leer
# una ruta como host).
host="$(printf '%s' "$comando_ejecutable" \
  | grep -oE -- '(^|[[:space:]])(--host|-h)[[:space:]=]*[^[:space:];|&]+' \
  | tail -n1 \
  | sed -E 's/^[[:space:]]*(--host|-h)[[:space:]=]*//' \
  | tr -d '\042\047')"

case "$host" in
  "")                        host_class="desconocido" ;;   # sin flag: sale del archivo de entorno
  @@HOSTS_LOCALES_CASE@@)    host_class="local" ;;
  *'$'*|*'`'*)               host_class="variable" ;;      # irresoluble para el hook
  *)                         host_class="remoto" ;;
esac

if [ "$host_class" = "remoto" ]; then
  deny "apunta al host '$host', que no es un host local declarado en la politica"
fi

if [ "$host_class" = "local" ]; then
  if solo_lectura_estricta cliente; then
    allow "SELECT de solo lectura contra un host local: autorizado sin preguntar"
  fi
  exit 0
fi

jq -n --arg reason "Consulta a la base en '$name' con host '${host:-no especificado, sale del archivo de entorno}': la politica permite SELECT de solo lectura SOLO contra un host local y el hook no puede resolver ese host (viene de una variable o del archivo de entorno). Confirmar que apunta a la base local antes de correr." \
  '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: $reason}}'
exit 0
