"""
Importa el CSV histórico (exportado de Google Sheets) a registro_movimiento.
Uso:
    python manage.py importar_historico ruta/al/csv.csv
    python manage.py importar_historico ruta/al/csv.csv --dry-run

- Usa la conexión 'carga' (rol auditoria_cargador) para los INSERT.
- Normaliza estados (trim + upper), parsea fechas con TZ Buenos Aires.
- Descarta filas sin comprobante y las reporta.
- Dedup por (tipo, comprobante, codigo).
- bulk_create en lotes de 500.
"""
import csv
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError

from apps.registros.models import RegistroMovimiento, TipoMovimiento


TZ = ZoneInfo('America/Argentina/Buenos_Aires')


def _to_int(v, default=0):
    try:
        return int(str(v).strip()) if str(v).strip() else default
    except (TypeError, ValueError):
        return default


def _parse_dt(s):
    """Fecha estilo '4/5/2026 7:17:22' → datetime con TZ AR."""
    s = (s or '').strip()
    if not s:
        return None
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=TZ)
        except ValueError:
            continue
    return None


def _norm(s):
    return (s or '').strip()


def _norm_tipo(s):
    t = _norm(s).lower()
    if t.startswith('env'):
        return TipoMovimiento.ENVIO
    if t.startswith('rec'):
        return TipoMovimiento.RECIBO
    return None


class Command(BaseCommand):
    help = 'Importa el histórico desde el CSV exportado de Google Sheets.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)
        parser.add_argument('--dry-run', action='store_true',
                            help='No escribe; sólo cuenta y reporta.')
        parser.add_argument('--batch', type=int, default=500)

    def handle(self, *args, **opts):
        path = opts['csv_path']
        dry = opts['dry_run']
        batch_size = opts['batch']

        total = ok = skipped = dupes = 0
        reasons = {}
        pendientes = []

        existentes = set()
        if not dry:
            # Pre-cargamos claves existentes para dedup rápido.
            existentes = set(
                RegistroMovimiento.objects
                .exclude(comprobante='')
                .values_list('tipo', 'comprobante', 'codigo')
            )

        try:
            f = open(path, newline='', encoding='utf-8')
        except FileNotFoundError:
            raise CommandError(f'No se encontró el archivo: {path}')

        with f:
            reader = csv.reader(f)
            next(reader, None)  # headers
            for i, row in enumerate(reader, start=2):
                total += 1
                if len(row) < 19:
                    row = row + [''] * (19 - len(row))

                dt = _parse_dt(row[0])
                if not dt:
                    reasons['fecha_invalida'] = reasons.get('fecha_invalida', 0) + 1
                    skipped += 1
                    continue

                tipo = _norm_tipo(row[3])
                if not tipo:
                    reasons['tipo_invalido'] = reasons.get('tipo_invalido', 0) + 1
                    skipped += 1
                    continue

                comprobante = _norm(row[12])
                codigo = _norm(row[6])
                if not comprobante:
                    reasons['sin_comprobante'] = reasons.get('sin_comprobante', 0) + 1
                    skipped += 1
                    continue
                if not codigo:
                    reasons['sin_codigo'] = reasons.get('sin_codigo', 0) + 1
                    skipped += 1
                    continue

                key = (tipo, comprobante, codigo)
                if key in existentes:
                    dupes += 1
                    continue

                pendientes.append(RegistroMovimiento(
                    creado_en_origen=dt,
                    email_carga=_norm(row[1]),
                    nombre_carga=_norm(row[2])[:120],
                    tipo=tipo,
                    sector_salida=_norm(row[4])[:60],
                    sector_entrada=_norm(row[5])[:60],
                    codigo=codigo[:50],
                    descripcion=_norm(row[7])[:160],
                    cantidad_bultos=_to_int(row[8]),
                    unidades_por_bulto=_to_int(row[9]),
                    unidades_sueltas=_to_int(row[10]),
                    observaciones=_norm(row[11]),
                    comprobante=comprobante[:30],
                    estado_concil=_norm(row[14])[:20].upper(),
                    estado_real=_norm(row[15])[:40].upper(),
                    obs_cande=_norm(row[16]),
                    flag_g3=_norm(row[17])[:30],
                    ref_bejerman=_norm(row[18])[:30],
                ))
                existentes.add(key)

                if not dry and len(pendientes) >= batch_size:
                    RegistroMovimiento.objects.bulk_create(pendientes)
                    ok += len(pendientes)
                    pendientes = []
                elif dry:
                    ok += 1

        if not dry and pendientes:
            RegistroMovimiento.objects.bulk_create(pendientes)
            ok += len(pendientes)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Total filas leídas: {total}'))
        self.stdout.write(self.style.SUCCESS(
            f'{"Serían insertadas" if dry else "Insertadas"}: {ok}'))
        if dupes:
            self.stdout.write(self.style.WARNING(f'Duplicadas (ya existían): {dupes}'))
        if skipped:
            self.stdout.write(self.style.WARNING(f'Descartadas: {skipped}'))
            for r, n in reasons.items():
                self.stdout.write(f'  · {r}: {n}')
        if dry:
            self.stdout.write(self.style.WARNING('(--dry-run: no se escribió nada)'))
