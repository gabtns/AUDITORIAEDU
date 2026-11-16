# Carga inicial del histórico

Script para subir las 4028 filas históricas desde Google Sheets a Supabase,
una sola vez.

## Paso a paso

### 1. Descargar la hoja como CSV

En Google Drive, abrí el archivo **SAA**.
`Archivo → Descargar → Valores separados por comas (.csv)`
Guardalo donde puedas verlo (ej. `~/Downloads/SAA-DATOS.csv`).

> Si la pestaña activa cuando descargás no es **DATOS**, cambiá primero a esa
> pestaña y después descargá. Google exporta sólo la pestaña activa.

### 2. Preparar las credenciales

El script usa dos variables de entorno:

```bash
export SUPABASE_URL=https://srawajdbyfipekprtmvb.supabase.co
export SUPABASE_KEY=eyJhbGciOi...     # service_role, la misma que Apps Script
```

(En Windows PowerShell: `$env:SUPABASE_URL = "..."` y `$env:SUPABASE_KEY = "..."`)

### 3. Dry-run — ver qué se va a cargar sin tocar la BD

```bash
python3 import_bulk.py ~/Downloads/SAA-DATOS.csv --dry-run
```

Te dice cuántas filas son válidas y cuántas se descartan (y por qué).

Ejemplo de salida esperado:

```
Leyendo CSV: /Users/.../SAA-DATOS.csv
Filas válidas: 3987
Filas descartadas: 41
  · sin_comprobante: 38
  · tipo_invalido: 3

(--dry-run: no se envía nada)
```

### 4. Carga real

Cuando el dry-run te convenza:

```bash
python3 import_bulk.py ~/Downloads/SAA-DATOS.csv
```

Manda en lotes de 500 por default. Si querés más chico:

```bash
python3 import_bulk.py ~/Downloads/SAA-DATOS.csv --batch 200
```

Salida esperada:

```
  [1/8] OK · HTTP 201 · 500/3987 acumuladas
  [2/8] OK · HTTP 201 · 1000/3987 acumuladas
  ...
  [8/8] OK · HTTP 201 · 3987/3987 acumuladas

==========================
Total enviadas: 3987
Lotes con error: 0
```

### 5. Verificar en Supabase

En el SQL Editor:

```sql
SELECT COUNT(*) FROM registro_movimiento;
SELECT sector_salida, COUNT(*)
FROM registro_movimiento
GROUP BY sector_salida
ORDER BY 2 DESC;
```

Debería devolver ~4000 filas y los sectores que conocés
(Produccion, G3-SEMI ELABORADOS, etc.).

## Idempotencia

Podés correr el script dos veces sin miedo. El endpoint usa
`Prefer: resolution=ignore-duplicates` + `on_conflict=tipo,comprobante,codigo`,
así que las filas que ya están en la BD se saltean en silencio. Lo que importa:
después de una corrida exitosa, un segundo run dice algo como:

```
Total enviadas: 3987   (pero de hecho ninguna se insertó: todas chocan con la UNIQUE)
```

(El contador cuenta filas enviadas, no filas realmente insertadas. Si querés
el número real, mirá `SELECT COUNT(*)` en Supabase antes y después.)

## Dependencias

Ninguna externa: usa sólo `urllib`, `csv`, `json`, `datetime`, `zoneinfo`.
Python ≥ 3.9. Si tenés Python más viejo, instalá `backports.zoneinfo` o
cambiá a `pytz`.

## Después

Una vez cargado el histórico, el Apps Script toma la posta: cada fila **nueva**
del Google Form se va a Supabase sola. Este script no se vuelve a usar salvo
que quieras rehacer una carga masiva desde cero.
