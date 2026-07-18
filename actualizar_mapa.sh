#!/bin/bash
# Regenera mapa_nimbo.html a partir del codigo actual del proyecto y lo copia
# al escritorio. Correr cuando quieras con:
#   bash actualizar_mapa.sh

set -e

# Se ubica la raiz del proyecto a partir de donde esta este script (no de
# donde se ejecuta el comando), para que funcione sin importar la carpeta
# actual desde la que se invoque.
DIR_PROYECTO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Analizando el codigo del proyecto..."
python3 "$DIR_PROYECTO/scripts/generar_mapa.py"

DESTINO_ESCRITORIO="$HOME/Desktop/mapa_nimbo.html"
cp "$DIR_PROYECTO/mapa_nimbo.html" "$DESTINO_ESCRITORIO"
echo "Copiado a: $DESTINO_ESCRITORIO"
