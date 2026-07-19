#!/usr/bin/env python3
"""
PostToolUse hook - Edit|Write

Corre `python3 -m py_compile` sobre el archivo que se acaba de escribir, si es
un .py. Si tiene un error de sintaxis, se lo devuelve a Claude como bloqueo
(decision: block) para que lo vea y lo corrija de inmediato, en vez de que el
error se descubra recien en el siguiente chequeo manual.

Escrito en Python (no bash+jq) porque jq no esta instalado en esta maquina, y
Python si esta garantizado (el proyecto entero lo requiere).

Recibe por stdin el JSON de entrada del hook (tool_name, tool_input, etc) y
escribe a stdout el JSON de salida del hook (o nada, si todo esta bien).
"""
import json
import subprocess
import sys


def main():
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    archivo = entrada.get("tool_input", {}).get("file_path", "")
    if not archivo.endswith(".py"):
        return 0

    resultado = subprocess.run(
        [sys.executable, "-m", "py_compile", archivo],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        error = (resultado.stderr or resultado.stdout).strip()
        salida = {
            "decision": "block",
            "reason": f"python3 -m py_compile encontro un error de sintaxis en "
                      f"{archivo}:\n\n{error}",
        }
        print(json.dumps(salida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
