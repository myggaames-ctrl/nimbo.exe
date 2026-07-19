---
name: documentar-bug
description: Documenta un bug encontrado y corregido (o una instalación/cambio de configuración) en las dos copias de BUGS_Y_FIXES.md del proyecto Nimbo, con el formato establecido. Usar al terminar de corregir un bug real, o de instalar/configurar algo nuevo (hook, skill, subagente, dependencia) que valga la pena dejar registrado. NO usar para features nuevas sin bug asociado (eso va en CLAUDE.md) ni para decisiones de arquitectura (eso va en DECISIONS.md).
---

# Documentar bug en BUGS_Y_FIXES.md

Empaqueta el flujo que se repitió muchas veces durante el desarrollo de Nimbo:
documentar un bug (o una instalación/cambio de configuración) en **las dos copias** de
`BUGS_Y_FIXES.md`, con el mismo formato, sin pisar nada de lo que ya existe.

## Cuándo usar este skill

- Se encontró y corrigió un bug real (algo que estaba roto y ahora funciona).
- Se instaló o configuró algo nuevo que otra persona (o Claude, en una sesión futura)
  necesita saber que existe y por qué se agregó (un hook, un skill, una dependencia).

**No usar para:**
- Documentar una feature nueva sin bug asociado - eso va en `CLAUDE.md`, sección
  "Módulos completados".
- Justificar una decisión de arquitectura (por qué X en vez de Y) - eso va en
  `DECISIONS.md`.

## Las dos rutas (SIEMPRE ambas, nunca solo una)

1. `~/nimbo.exe/BUGS_Y_FIXES.md` (raíz del proyecto)
2. `~/Desktop/Terminologia y Estudio de Codigo Nimbo/BUGS_Y_FIXES.md` (escritorio)

Al terminar, verificar que quedaron idénticas con `diff`.

## Formato de la entrada

Cada entrada se **agrega al final del archivo** (nunca se edita ni se borra una entrada
existente). Formato exacto:

```markdown
---

## [FECHA] Título corto y descriptivo

**Problema:** qué pasaba - el síntoma que veía el usuario, en español simple.

**Causa:** por qué pasaba - la causa técnica real, no solo la superficial. Si la causa
real resultó ser más profunda de lo que parecía al principio, decirlo explícitamente
(ver ejemplos de bugs anteriores en el archivo - varios empezaron pareciendo un problema
chico y resultaron ser algo más grande).

**Solución:** qué se hizo para arreglarlo, con suficiente detalle técnico para que
alguien pueda entender el cambio sin tener que leer el diff completo. Si se verificó de
alguna forma (con una prueba, comparando antes/después, etc.), decir cómo.

**Archivos modificados:** lista de archivos tocados (rutas relativas al proyecto).
```

`FECHA` en formato `YYYY-MM-DD` (correr `date +%Y-%m-%d` si no se sabe la fecha actual).

## Pasos

1. **Conseguir la fecha actual**: `date +%Y-%m-%d`.

2. **Leer el final de la copia en la raíz** para saber dónde termina el contenido
   actual (nunca asumir, siempre verificar):
   ```bash
   tail -10 ~/nimbo.exe/BUGS_Y_FIXES.md
   ```

3. **Redactar la entrada** siguiendo el formato de arriba. Ser específico y técnico -
   estas entradas las lee gente aprendiendo a programar (ver `GLOSARIO.md`), así que
   los términos técnicos que no sean obvios deberían poder buscarse ahí.

4. **Agregar la entrada al final de la copia en la raíz** (`~/nimbo.exe/BUGS_Y_FIXES.md`)
   usando una edición que solo AGREGUE texto después del contenido existente - nunca
   reemplazar ni borrar nada de lo que ya está.

5. **Repetir exactamente el mismo texto** en la copia del escritorio
   (`~/Desktop/Terminologia y Estudio de Codigo Nimbo/BUGS_Y_FIXES.md`).

6. **Verificar que ambas copias quedaron idénticas**:
   ```bash
   diff "~/nimbo.exe/BUGS_Y_FIXES.md" "~/Desktop/Terminologia y Estudio de Codigo Nimbo/BUGS_Y_FIXES.md" && echo "Ambas copias identicas"
   ```
   Si `diff` muestra algo, corregir antes de continuar - las dos copias SIEMPRE tienen
   que quedar exactamente iguales.

7. Si aparecen términos técnicos nuevos en la entrada que no están en `GLOSARIO.md`,
   considerar agregarlos ahí también (mismo criterio: `grep -i "termino" GLOSARIO.md`
   antes de agregar, solo agregar si no existe).

## Ejemplo real (de esta misma sesión)

```markdown
---

## [2026-07-18] crear_empresa() creaba una base de datos con 19 tablas faltantes

**Problema:** una empresa nueva registrada vía `crear_empresa()` (por ejemplo Surti La
Unión) quedaba sin las tablas `PagoFijo`, `HistorialPrecio`, `Gasto`, `Kardex`, `Venta`,
y otras 14 más...

**Por qué pasaba (causa real, más profunda de lo que parecía al principio):** no era que
`crear_empresa()` se olvidara de llamar a algunas funciones `init_*` que ya existían -
al revisar, no existía ningún `init_*` para esas 19 tablas en absoluto...

**Cómo se arregló:** se agregaron 10 funciones `init_*` nuevas...

**Archivos modificados:** `database/nimbo_db.py`, `core/empresa.py`, y
`data/empresas/surti-la-union/nimbo.db`.
```
