# {{nombre}}

Entorno de trabajo para agentes de programación, generado por **meta-harness {{version_origen}}** el {{fecha}}.
Es **independiente**: no necesita el meta-harness para funcionar ni para actualizarse. Lo que contiene es tuyo.

## Qué trae (módulos elegidos)

{{lista_modulos}}

## Cómo se usa

1. `./instalar.sh` muestra qué hace falta en tu máquina (solo lee) y `./instalar.sh --aplicar` deja el repo listo.
2. Abre esta carpeta con tu agente. {{nota_agentes}}
3. `./verificar.sh` comprueba que el entorno está sano. `./scripts/gate.sh` es la compuerta antes de entregar.

## Cómo se cambia

Todo está en `entorno.toml` (módulos, comandos de la compuerta, rutas de documentación, autoguardado). Cada script es de
lectura corta y se puede editar. Las reglas aprendidas con evidencia se promueven con `scripts/aprender.py` y se pueden revertir.

Licencia Apache-2.0 (ver `LICENSE` y `NOTICE`). Origen y qué se copió: `docs/ORIGEN.md`.
