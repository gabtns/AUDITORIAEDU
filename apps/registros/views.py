"""
Dashboard de conciliación:
- Filtros: mes/año (col A) y código de artículo (col G)
- Dos columnas lado a lado:
  * Producción (col E == 'Produccion')
  * G1 / G3   (col F in {'G1-LOGISTICA', 'G3-SEMI ELABORADOS'})
- Sumatoria al pie de cada lado + diferencia para saber si el artículo "está".
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from django.shortcuts import render
from django.utils import timezone

from .models import RegistroMovimiento


TZ = ZoneInfo('America/Argentina/Buenos_Aires')
SECTOR_PROD = 'Produccion'
SECTORES_G1G3 = ['G1-LOGISTICA', 'G3-SEMI ELABORADOS']
TIPO_ENVIO = 'envio'
TIPO_RECIBO = 'recibo'

MESES_ES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']


def _meses_disponibles():
    """Lista de (valor_'YYYY-MM', label_'Octubre 2026') con datos en BD."""
    qs = (RegistroMovimiento.objects
          .annotate(y=ExtractYear('creado_en_origen'),
                    m=ExtractMonth('creado_en_origen'))
          .values('y', 'm').distinct().order_by('-y', '-m'))
    salida = []
    for row in qs:
        y, m = row['y'], row['m']
        if not y or not m:
            continue
        salida.append((f'{y}-{m:02d}', f'{MESES_ES[m]} {y}'))
    return salida


def _codigos_disponibles():
    """Lista plana de códigos únicos, ordenados."""
    return list(RegistroMovimiento.objects
                .exclude(codigo='')
                .values_list('codigo', flat=True)
                .distinct()
                .order_by('codigo'))


def _rango_del_mes(mes_str: str) -> tuple[datetime, datetime]:
    """'2026-11' → (inicio_de_nov_2026, inicio_de_dic_2026)."""
    y, m = map(int, mes_str.split('-'))
    desde = datetime(y, m, 1, tzinfo=TZ)
    # Primer día del mes siguiente
    if m == 12:
        hasta = datetime(y + 1, 1, 1, tzinfo=TZ)
    else:
        hasta = datetime(y, m + 1, 1, tzinfo=TZ)
    return desde, hasta


@login_required
def dashboard(request):
    # ---------- Filtros ----------
    mes = request.GET.get('mes', '').strip()
    codigo = request.GET.get('codigo', '').strip()

    meses = _meses_disponibles()
    codigos = _codigos_disponibles()

    # Default: mes más reciente con datos (o el actual si no hay datos)
    if not mes:
        mes = meses[0][0] if meses else timezone.now().astimezone(TZ).strftime('%Y-%m')

    desde, hasta = _rango_del_mes(mes)

    # ---------- Querys ----------
    base = RegistroMovimiento.objects.filter(
        creado_en_origen__gte=desde,
        creado_en_origen__lt=hasta,
    )
    if codigo:
        base = base.filter(codigo=codigo)

    # Producción: solo ENVÍOS que salen de Producción (tipo='envio' + sector_salida='Produccion')
    # Excluye los recibos de G3/G1 donde sector_salida='Produccion' (esos son confirmaciones externas)
    prod_qs = base.filter(
        tipo__iexact=TIPO_ENVIO,
        sector_salida=SECTOR_PROD,
    ).order_by('-creado_en_origen')
    prod_rows = list(prod_qs)
    prod_sum = prod_qs.aggregate(s=Sum('cantidad_total'))['s'] or 0

    # G1 / G3: solo RECIBOS que entran a G1 o G3 (tipo='recibo' + sector_entrada in G1/G3)
    # Excluye los envíos de Producción que tienen sector_entrada='G3-SEMI ELABORADOS'
    g1g3_qs = base.filter(
        tipo__iexact=TIPO_RECIBO,
        sector_entrada__in=SECTORES_G1G3,
    ).order_by('-creado_en_origen')
    g1g3_rows = list(g1g3_qs)
    g1g3_sum = g1g3_qs.aggregate(s=Sum('cantidad_total'))['s'] or 0

    diferencia = prod_sum - g1g3_sum

    ctx = {
        'meses': meses,
        'codigos': codigos,
        'mes_sel': mes,
        'codigo_sel': codigo,
        'prod_rows': prod_rows,
        'prod_sum': prod_sum,
        'g1g3_rows': g1g3_rows,
        'g1g3_sum': g1g3_sum,
        'diferencia': diferencia,
    }
    return render(request, 'registros/dashboard.html', ctx)
