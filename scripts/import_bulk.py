#!/usr/bin/env python3
"""
import_bulk.py
Carga masiva del CSV histórico (exportado de Google Sheets) a Supabase.

Uso:
    export SUPABASE_URL=https://srawajdbyfipekprtmvb.supabase.co
    export SUPABASE_KEY=eyJhbGciOi...     # service_role key
    python3 import_bulk.py historico.csv
    python3 import_bulk.py historico.csv --dry-run
    python3 import_bulk.py historico.csv --batch 500

Sin dependencias externas: usa sólo la stdlib (urllib, csv, json).

Qué hace:
- Lee cada fila del CSV (columnas A..S del Google Form)
- Normaliza tipo, estados (trim+upper) y fechas (TZ Buenos Aires)
- Descarta filas sin tipo, sin comprobante o sin código, y reporta cuántas
- Manda lotes al endpoint PostgREST con Prefer: resolution=ignore-duplicates
  (choca contra la UNIQUE (tipo, comprobante, codigo) → se ignora, no rompe)
"""
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from zoneinfo import ZoneInfo


TZ = ZoneInfo('America/Argentina/Buenos_Aires')


def norm_tipo(s):
    t = (s or '').strip().lower()
    if t.startswith('env'):
        return 'envio'
    if t.startswith('rec'):
        return 'recibo'
    return None


def to_int(v, default=0):
    try:
        return int(str(v).strip()) if str(v).strip() else default
    except (TypeError, ValueError):
        return default


def parse_dt_iso(s):
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=TZ)
            return dt.isoformat()
        except ValueError:
            continue
    return None


def leer_csv(path):
    """Devuelve (records válidos, dict con razones de descarte)."""
    records = []
    reasons = {}
    with open(path, newline='', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        next(reader, None)  # headers
        for row in reader:
            if len(row) < 19:
                row = list(row) + [''] * (19 - len(row))

            dt = parse_dt_iso(row[0])
            tipo = norm_tipo(row[3])
            comprobante = (row[12] or '').strip()
            codigo = (row[6] or '').strip()

            if not dt:
                reasons['fecha_invalida'] = reasons.get('fecha_invalida', 0) + 1
                continue
            if not tipo:
                reasons['tipo_invalido'] = reasons.get('tipo_invalido', 0) + 1
                continue
            if not codigo:
                reasons['sin_codigo'] = reasons.get('sin_codigo', 0) + 1
                continue
            # Nota: las filas sin comprobante entran. El UNIQUE sólo dedupea
            # cuando hay comprobante (WHERE comprobante <> ''), así que si
            # corrés el script dos veces, las filas sin comprobante se
            # duplican. Correr este script UNA sola vez para la carga inicial.

            records.append({
                'creado_en_origen':   dt,
                'email_carga':        (row[1] or '').strip()[:160],
                'nombre_carga':       (row[2] or '').strip()[:120],
                'tipo':               tipo,
                'sector_salida':      (row[4] or '').strip()[:60],
                'sector_entrada':     (row[5] or '').strip()[:60],
                'codigo':             codigo[:50],
                'descripcion':        (row[7] or '').strip()[:160],
                'cantidad_bultos':    to_int(row[8]),
                'unidades_por_bulto': to_int(row[9]),
                'unidades_sueltas':   to_int(row[10]),
                'observaciones':      row[11] or '',
                'comprobante':        comprobante[:30],
                'estado_concil':      (row[14] or '').strip().upper()[:20],
                'estado_real':        (row[15] or '').strip().upper()[:40],
                'obs_cande':          row[16] or '',
                'flag_g3':            (row[17] or '').strip()[:30],
                'ref_bejerman':       (row[18] or '').strip()[:30],
            })
    return records, reasons


def enviar_lote(endpoint, key, batch):
    body = json.dumps(batch).encode('utf-8')
    req = urllib.request.Request(
        endpoint, data=body, method='POST',
        headers={
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json',
            # ignore-duplicates: si la UNIQUE pega, no rompe el lote
            'Prefer': 'return=minimal,resolution=ignore-duplicates',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.getcode(), ''
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode('utf-8', 'ignore')[:400]
        except Exception:
            msg = ''
        return e.code, msg
    except urllib.error.URLError as e:
        return 0, f'url_error: {e.reason}'


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)

    csv_path = args[0]
    dry = '--dry-run' in args
    batch_size = 500
    if '--batch' in args:
        try:
            batch_size = int(args[args.index('--batch') + 1])
        except (IndexError, ValueError):
            print('ERROR: --batch requiere un número')
            sys.exit(2)

    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_KEY', '')
    if not dry and (not url or not key):
        print('ERROR: setear SUPABASE_URL y SUPABASE_KEY en el entorno.')
        print('Ej:  export SUPABASE_URL=https://xxx.supabase.co')
        print('     export SUPABASE_KEY=eyJhbGciOi...')
        sys.exit(2)

    endpoint = (url.rstrip('/') +
                '/rest/v1/registro_movimiento'
                '?on_conflict=tipo,comprobante,codigo')

    print(f'Leyendo CSV: {csv_path}')
    records, reasons = leer_csv(csv_path)

    total_desc = sum(reasons.values())
    print(f'Filas válidas: {len(records)}')
    print(f'Filas descartadas: {total_desc}')
    for r, n in reasons.items():
        print(f'  · {r}: {n}')

    if dry:
        print('\n(--dry-run: no se envía nada)')
        if records:
            print('Primer registro de ejemplo:')
            print(json.dumps(records[0], ensure_ascii=False, indent=2))
        return

    if not records:
        print('No hay nada para enviar.')
        return

    print(f'\nEnviando a {endpoint[:80]}...')
    print(f'Lotes de {batch_size} filas\n')

    enviadas = errores = 0
    total_lotes = (len(records) + batch_size - 1) // batch_size
    for i in range(0, len(records), batch_size):
        lote = records[i:i + batch_size]
        n_lote = i // batch_size + 1
        code, msg = enviar_lote(endpoint, key, lote)
        if 200 <= code < 300:
            enviadas += len(lote)
            print(f'  [{n_lote}/{total_lotes}] OK · HTTP {code} · '
                  f'{enviadas}/{len(records)} acumuladas')
        else:
            errores += 1
            print(f'  [{n_lote}/{total_lotes}] ERR · HTTP {code} · {msg}')
            # Si falla un lote entero, seguimos con el próximo.
        time.sleep(0.2)   # no saturar la API

    print('\n==========================')
    print(f'Total enviadas: {enviadas}')
    print(f'Lotes con error: {errores}')
    if enviadas:
        print('Verificá en Supabase:')
        print('  SELECT COUNT(*) FROM registro_movimiento;')


if __name__ == '__main__':
    main()
