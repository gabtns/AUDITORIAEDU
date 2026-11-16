from django.contrib import admin
from .models import RegistroMovimiento


@admin.register(RegistroMovimiento)
class RegistroAdmin(admin.ModelAdmin):
    list_display = ('creado_en_origen', 'tipo', 'sector_salida',
                    'sector_entrada', 'codigo', 'comprobante',
                    'cantidad_bultos', 'unidades_por_bulto',
                    'unidades_sueltas', 'cantidad_total')
    list_filter = ('tipo', 'sector_salida', 'sector_entrada', 'estado_concil')
    search_fields = ('codigo', 'comprobante', 'descripcion', 'nombre_carga')
    date_hierarchy = 'creado_en_origen'
