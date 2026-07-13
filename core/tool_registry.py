"""
Tool Registry
Mi Cocina AI
"""

from typing import Callable

TOOLS = {}


def register(name: str, function: Callable):
    """
    Registra una herramienta.
    """
    TOOLS[name] = function


def get(name: str):
    """
    Obtiene una herramienta.
    """
    return TOOLS.get(name)


def exists(name: str):
    """
    Verifica si existe.
    """
    return name in TOOLS


def list_tools():
    """
    Devuelve todas las herramientas registradas.
    """
    return sorted(TOOLS.keys())