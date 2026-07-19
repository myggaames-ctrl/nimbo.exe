#!/usr/bin/env python3
"""
PreToolUse hook - Edit|Write

Bloquea cualquier intento de editar/escribir un archivo *.db directamente
(nimbo.db, nimbo_master.db, data/empresas/*/nimbo.db, aronium_demo.db, etc).
Esos archivos son bases de datos SQLite reales con datos de negocio - se deben
tocar solo a traves de las funciones de la app (database/nimbo_db.py,
core/auth.py, core/empresa.py, core/configuracion.py) o con el cliente
`sqlite3` desde una Bash, nunca como edicion de archivo binario con Edit/Write
(eso corrompe el archivo, no es un formato de texto).

Recibe por stdin el JSON de entrada del hook y escribe a stdout el JSON de
salida (permissionDecision: deny) si corresponde bloquear.
"""
import json
import sys


def main():
    try:
        entrada = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    archivo = entrada.get("tool_input", {}).get("file_path", "")
    if not archivo.endswith(".db"):
        return 0

    salida = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{archivo} es una base de datos SQLite real, no un archivo de "
                "texto - editarla directamente con Edit/Write la corrompe. Usa "
                "las funciones de database/nimbo_db.py, core/auth.py, "
                "core/empresa.py o core/configuracion.py, o el cliente `sqlite3` "
                "desde Bash."
            ),
        }
    }
    print(json.dumps(salida))
    return 0


if __name__ == "__main__":
    sys.exit(main())
