"""
Herramientas de Windows
"""

import subprocess

from core.tool_registry import register


def open_app(app):

    apps = {

        "bloc": "notepad.exe",
        "bloc de notas": "notepad.exe",
        "notepad": "notepad.exe",

        "calculadora": "calc.exe",
        "calc": "calc.exe",

        "explorador": "explorer.exe",
        "explorer": "explorer.exe",

        "cmd": "cmd.exe",

        "powershell": "powershell.exe"

    }

    command = apps.get(app.lower())

    if not command:

        return f"No conozco la aplicación '{app}'."

    try:

        subprocess.Popen(
            ["powershell.exe", "-Command", command]
        )

        return f"Abrí {app}."

    except Exception as e:

        return str(e)


register(
    "windows.open_app",
    open_app
)