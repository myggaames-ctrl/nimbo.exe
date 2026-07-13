"""
Carga automática de todas las Tools
"""

import pkgutil
import importlib


for module in pkgutil.iter_modules(__path__):

    if module.name.startswith("_"):
        continue

    importlib.import_module(
        f"{__name__}.{module.name}"
    )