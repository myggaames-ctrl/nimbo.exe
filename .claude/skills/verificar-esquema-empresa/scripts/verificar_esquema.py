#!/usr/bin/env python3
"""
Verifica que el esquema de nimbo.db sea consistente, de dos formas:

1. Compara ".tables" entre dos bases de datos reales (por defecto: Mi Cocina
   contra todas las demas empresas de data/empresas/) - encuentra tablas que
   le faltan a una empresa respecto a otra.

2. Cruza, en el CODIGO (no en una base de datos ya creada), cada tabla
   referenciada en SQL (FROM/INTO/UPDATE) contra las que tienen un
   "CREATE TABLE" en algun init_* - encuentra tablas que el codigo activo usa
   pero que ningun init_* crearia para una empresa nueva. Esto es lo que
   habria encontrado el bug real de las 19 tablas faltantes (2026-07-18,
   ver BUGS_Y_FIXES.md) ANTES de que llegara a producción.

Uso:
    python3 verificar_esquema.py                  # ambos chequeos, contra Mi Cocina
    python3 verificar_esquema.py --solo-codigo     # solo el chequeo 2 (no necesita bases de datos creadas)
    python3 verificar_esquema.py --base mi-cocina --contra surti-la-union
"""
import argparse
import ast
import os
import re
import sqlite3
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# .claude/skills/verificar-esquema-empresa/scripts/ -> raiz del proyecto (5 niveles
# arriba: scripts -> verificar-esquema-empresa -> skills -> .claude -> raiz)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR))))

ARCHIVOS_SQL = [
    "database/nimbo_db.py",
    "core/auth.py",
    "core/configuracion.py",
    "core/empresa.py",
]



def tablas_creadas_por_codigo():
    """Todas las tablas con un CREATE TABLE (IF NOT EXISTS opcional) en los
    archivos que definen el esquema."""
    tablas = set()
    patron = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)
    for rel in ARCHIVOS_SQL:
        ruta = os.path.join(BASE_DIR, rel)
        if not os.path.isfile(ruta):
            continue
        codigo = open(ruta, encoding="utf-8").read()
        tablas.update(patron.findall(codigo))
    return tablas


def tablas_usadas_por_codigo():
    """Todas las tablas referenciadas en FROM/INTO/UPDATE (uso real de datos,
    no creacion) en los mismos archivos - incluye tools/ y services/ tambien,
    por si algun modulo hace SQL directo fuera de database/nimbo_db.py.

    Solo mira dentro de literales de string (comillas simples/dobles/triples),
    nunca la linea completa - si no, el patron FROM (case-insensitive, para
    aceptar "from Cliente" igual que "FROM Cliente") tambien matchea el
    "from X import Y" de Python y contamina el resultado con nombres de
    modulo (core, database, flask, etc) en vez de tablas."""
    tablas = set()
    patron_sql = re.compile(r"\b(?:FROM|INTO|UPDATE)\s+(\w+)", re.IGNORECASE)
    partes_patron_strings = [
        r'"""(.*?)"""',
        r"'''(.*?)'''",
        r'"([^"\n]*)"',
        r"'([^'\n]*)'",
    ]
    patron_strings = re.compile("|".join(partes_patron_strings), re.DOTALL)
    carpetas = ["database", "core", "tools", "services"]
    for carpeta in carpetas:
        ruta_carpeta = os.path.join(BASE_DIR, carpeta)
        if not os.path.isdir(ruta_carpeta):
            continue
        for raiz, _, archivos in os.walk(ruta_carpeta):
            if "__pycache__" in raiz:
                continue
            for nombre in archivos:
                if not nombre.endswith(".py"):
                    continue
                ruta = os.path.join(raiz, nombre)
                try:
                    codigo = open(ruta, encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    continue
                for grupos in patron_strings.findall(codigo):
                    literal = next((g for g in grupos if g), "")
                    tablas.update(patron_sql.findall(literal))
    # nombres que no son tablas reales (falsos positivos comunes del patron regex):
    # sqlite_master/sqlite_sequence son tablas internas de SQLite, no del esquema
    # propio; SET aparece en "ON CONFLICT(...) DO UPDATE SET col = ..." (upsert sin
    # nombre de tabla repetido despues de UPDATE); "de" aparece en comentarios en
    # espanol como "...haga UPDATE de esa tabla..." (prosa, no SQL real) - ambos son
    # ruido de que el regex no distingue SQL real de texto libre dentro de un string.
    tablas -= {"sqlite_master", "sqlite_sequence", "SET", "de"}
    return tablas


def chequeo_codigo():
    creadas = tablas_creadas_por_codigo()
    usadas = tablas_usadas_por_codigo()
    faltantes = sorted(usadas - creadas)

    print(f"Tablas con CREATE TABLE en el codigo: {len(creadas)}")
    print(f"Tablas referenciadas (FROM/INTO/UPDATE) en el codigo: {len(usadas)}")
    print()
    if faltantes:
        print(f"⚠ {len(faltantes)} tabla(s) USADA(S) por el codigo pero SIN ningun "
              f"CREATE TABLE que las cree:")
        for t in faltantes:
            print(f"   - {t}")
        print()
        print("Esto significa que una empresa nueva (creada con core.empresa."
              "crear_empresa()) probablemente no tendria estas tablas - el mismo tipo "
              "de bug que paso el 2026-07-18. Revisar si hace falta un init_* nuevo.")
        return False
    else:
        print("✓ Todas las tablas usadas por el codigo tienen un CREATE TABLE en algun init_*.")
        return True


def chequeo_bases_de_datos(base_slug, contra_slug=None):
    empresas_dir = os.path.join(BASE_DIR, "data", "empresas")
    if not os.path.isdir(empresas_dir):
        print("No existe data/empresas/ - no hay bases de datos que comparar todavia.")
        return True

    base_db = os.path.join(empresas_dir, base_slug, "nimbo.db")
    if not os.path.isfile(base_db):
        print(f"No se encontro {base_db}")
        return False

    def tablas_de(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        nombres = {r[0] for r in cur.fetchall()}
        conn.close()
        return nombres

    tablas_base = tablas_de(base_db)

    if contra_slug:
        candidatos = [contra_slug]
    else:
        candidatos = sorted(
            d for d in os.listdir(empresas_dir)
            if d != base_slug and os.path.isfile(os.path.join(empresas_dir, d, "nimbo.db"))
        )

    ok = True
    for slug in candidatos:
        db_path = os.path.join(empresas_dir, slug, "nimbo.db")
        tablas_otra = tablas_de(db_path)
        faltan = sorted(tablas_base - tablas_otra)
        sobran = sorted(tablas_otra - tablas_base)
        if not faltan and not sobran:
            print(f"✓ {slug}: mismas tablas que {base_slug} ({len(tablas_otra)} tablas)")
        else:
            ok = False
            print(f"⚠ {slug}: esquema distinto de {base_slug}")
            if faltan:
                print(f"   Le faltan {len(faltan)}: {', '.join(faltan)}")
            if sobran:
                print(f"   Tiene de mas {len(sobran)}: {', '.join(sobran)}")
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="mi-cocina", help="slug de la empresa de referencia (default: mi-cocina)")
    parser.add_argument("--contra", default=None, help="slug de una empresa especifica a comparar (default: todas)")
    parser.add_argument("--solo-codigo", action="store_true", help="solo correr el chequeo de codigo, sin tocar bases de datos")
    args = parser.parse_args()

    print("=== 1. Tablas usadas por el codigo vs tablas creadas por algun init_* ===\n")
    ok1 = chequeo_codigo()

    ok2 = True
    if not args.solo_codigo:
        print(f"\n=== 2. Comparando .tables de cada empresa contra '{args.base}' ===\n")
        ok2 = chequeo_bases_de_datos(args.base, args.contra)

    print()
    if ok1 and ok2:
        print("Todo consistente.")
        sys.exit(0)
    else:
        print("Se encontraron inconsistencias - ver arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()
