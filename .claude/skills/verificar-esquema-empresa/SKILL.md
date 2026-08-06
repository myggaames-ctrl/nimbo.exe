---
name: verificar-esquema-empresa
description: Verifica que el esquema de base de datos de Nimbo sea consistente entre empresas (multi-tenant) y entre el codigo y las bases de datos reales. Usar despues de agregar una tabla nueva, una funcion init_* nueva, o cambiar core/empresa.py - y periodicamente para detectar bases de datos de empresa que quedaron con un esquema incompleto (mismo tipo de bug que crear_empresa() el 2026-07-18, ver BUGS_Y_FIXES.md).
---

# Verificar esquema de empresa

Corre `scripts/verificar_esquema.py`, que hace dos chequeos independientes sobre el
sistema multi-tenant de Nimbo (`core/empresa.py`, `data/empresas/<slug>/nimbo.db`):

1. **Codigo vs codigo**: cruza cada tabla que el codigo usa de verdad (`FROM`/`INTO`/
   `UPDATE` dentro de queries SQL reales, no de comentarios) contra las tablas que
   algun `init_*` de `database/nimbo_db.py`, `core/auth.py`, `core/configuracion.py` o
   `core/empresa.py` efectivamente crea con `CREATE TABLE`. Si una tabla se usa pero
   ningun `init_*` la crearia, una empresa nueva se quedaria sin ella - exactamente el
   bug real que paso el 2026-07-18 con `crear_empresa()` (19 tablas faltantes).
2. **Base de datos vs base de datos**: compara el `.tables` real de cada
   `data/empresas/<slug>/nimbo.db` contra el de Mi Cocina (`mi-cocina`, la empresa de
   referencia porque es la mas antigua y completa). Encuentra empresas cuya base de
   datos ya quedo con un esquema incompleto (creadas con una version vieja y rota de
   `crear_empresa()`, antes de un fix).

## Cuando usar este skill

- Se agrego una tabla nueva a Nimbo (un `CREATE TABLE` nuevo en cualquier `init_*`).
- Se modifico `core/empresa.py._inicializar_tablas_empresa()` (que funciones llama y
  en que orden).
- Se sospecha que una empresa (ver `nimbo_master.db`, tabla `Empresa`) tiene una base
  de datos con tablas faltantes - por ejemplo, un error `sqlite3.OperationalError: no
  such table` reportado desde el chat de una empresa que no sea Mi Cocina.
- Como chequeo periodico de salud del sistema multi-tenant, sin motivo especifico.

## Como correrlo

```bash
cd ~/nimbo.exe
python3 .claude/skills/verificar-esquema-empresa/scripts/verificar_esquema.py
```

Sale con codigo 0 si todo esta consistente, o 1 si encontro algo. Opciones:

- `--solo-codigo`: solo el chequeo 1 (no necesita que existan bases de datos de
  empresa creadas todavia - util para revisar el codigo antes de haber probado nada).
- `--base <slug>`: cambiar la empresa de referencia del chequeo 2 (default
  `mi-cocina`).
- `--contra <slug>`: comparar el chequeo 2 solo contra una empresa especifica en vez
  de todas las que haya en `data/empresas/`.

## Que significa cada resultado

**Chequeo 1 encuentra una tabla faltante:** falta una funcion `init_*` (o falta
agregar una ya existente a `ARCHIVOS_SQL` en el script, si la tabla se crea en un
archivo que el script todavia no escanea) y falta agregarla a la lista de
`core/empresa.py._inicializar_tablas_empresa()`. Ver el bug real del 2026-07-18 en
`BUGS_Y_FIXES.md` para el patron completo de la solucion (10 funciones `init_*`
nuevas, agregadas ANTES de las que hacen `ALTER TABLE` sobre esas mismas tablas).

**Chequeo 2 encuentra una empresa con tablas faltantes:** su `nimbo.db` se creo con
una version vieja/rota de `crear_empresa()`, antes de que se agregara el `init_*` que
le faltaba. La solucion (ya probada seguro dos veces - Surti La Union y tienda del
chino, ver `BUGS_Y_FIXES.md`) es correr `core.empresa._inicializar_tablas_empresa()`
directo contra el `nimbo.db` de esa empresa: todas las funciones que llama son
`CREATE TABLE IF NOT EXISTS` o `ALTER TABLE` con manejo de "la columna ya existe", asi
que es seguro correrlas de nuevo sobre una base de datos que ya tiene datos - no borra
ni pisa nada existente.

```bash
python3 -c "
from core.empresa import _inicializar_tablas_empresa
import os
db_path = os.path.abspath('data/empresas/<slug>/nimbo.db')
_inicializar_tablas_empresa(db_path)
"
```

Verificar despues con el mismo `verificar_esquema.py` que la empresa ya matchea, y que
sus datos (ej. `SELECT * FROM Usuario`) siguen intactos.

## Limitaciones conocidas (por diseno, no son bugs)

- El regex que busca uso de tablas solo mira dentro de literales de string (comillas
  simples, dobles o triples) del codigo Python, para no confundir el `FROM` de SQL con
  el `from X import Y` de Python. Dos palabras sueltas dentro de comentarios/
  docstrings en espanol (`SET`, `de`) quedan excluidas a mano porque coinciden con
  texto libre, no con SQL real - si aparece un falso positivo nuevo de este tipo,
  agregarlo al mismo set de exclusion en `tablas_usadas_por_codigo()` en vez de
  ignorar el resultado del script.
