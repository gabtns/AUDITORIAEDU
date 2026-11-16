"""
Dashboard: muestra registros del mes actual y anterior (toggle para +1 mes),
separados en Producción | G3-SEMI ELABORADOS, con sumatoria al pie.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .models import RegistroMovimiento


TZ = ZoneInfo('America/Argentina/Buenos_Aires')
SECTOR_PROD = 'Produccion'
SECTOR_G3 = 'G3-SEMI ELABORADOS'


def _inicio_de_mes(ref: datetime) -> datetime:
    return ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _mes_anterior(ref: datetime) -> datetime:
    return _inicio_de_mes(_inicio_de_mes(ref) - timedelta(days=1))


def _rango_meses(expandir: bool) -> tuple[datetime, datetime]:
    """
    (desde, hasta) según el toggle.
    - expandir=False → mes actual + mes anterior (2 meses)
    - expandir=True  → mes actual + 2 meses anteriores (3 meses)
    """
    ahora = timezone.now().astimezone(TZ)
    actual = _inicio_de_mes(ahora)
    anterior = _mes_anterior(actual)
    desde = _mes_anterior(anterior) if expandir else anterior
    hasta = _inicio_de_mes(actual + timedelta(days=32))
    return desde, hasta


def _consultar(sector: str, desde: datetime, hasta: datetime):
    """
    Trae los registros de un sector en el rango, ordenados descendente.
    Usa CANTIDAD TOTAL como total_unidades (ya viene calculada en la hoja/BD).
    """
    qs = (RegistroMovimiento.objects
          .filter(sector_salida=sector,
                  creado_en_origen__gte=desde,
                  creado_en_origen__lt=hasta)
          .order_by('-creado_en_origen'))
    sumatoria = qs.aggregate(s=Sum('cantidad_total'))['s'] or 0
    return list(qs), sumatoria


@login_required
def dashboard(request):
    expandir = request.GET.get('expandir') == '1'
    desde, hasta = _rango_meses(expandir)

    prod_rows, prod_sum = _consultar(SECTOR_PROD, desde, hasta)
    g3_rows, g3_sum = _consultar(SECTOR_G3, desde, hasta)

    ctx = {
        'expandir': expandir,
        'desde': desde,
        'hasta': hasta,
        'prod_rows': prod_rows,
        'prod_sum': prod_sum,
        'g3_rows': g3_rows,
        'g3_sum': g3_sum,
    }
    return render(request, 'registros/dashboard.html', ctx)
