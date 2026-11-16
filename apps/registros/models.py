"""
Modelo central: RegistroMovimiento.
Mapea los nombres LITERALES de columna que quedaron en Supabase
(con mayúsculas, espacios, tildes y el "?"), vía db_column=.
La tabla la crea/mantiene Supabase; Django sólo lee (managed=False).
"""
from django.db import models


class RegistroMovimiento(models.Model):
    # Django exige una PK. Si tu tabla no tenía una, corré:
    # ALTER TABLE registro_movimiento ADD COLUMN IF NOT EXISTS id BIGSERIAL PRIMARY KEY;
    id = models.BigAutoField(primary_key=True)

    creado_en_origen = models.DateTimeField(
        db_column='Marca temporal', db_index=True)
    email_carga = models.CharField(
        db_column='Dirección de correo electrónico', max_length=160, blank=True)
    nombre_carga = models.CharField(
        db_column='Nombre y apellido', max_length=120, blank=True)
    tipo = models.CharField(
        db_column='Envias o recibis mercaderia?', max_length=20, db_index=True)
    sector_salida = models.CharField(
        db_column='SECTOR DE SALIDA', max_length=60, db_index=True)
    sector_entrada = models.CharField(
        db_column='SECTOR DE ENTRADA', max_length=60, blank=True)
    codigo = models.CharField(
        db_column='CODIGO DEL ARTICULO', max_length=50, db_index=True)
    descripcion = models.CharField(
        db_column='DESCIPCION DE ARTICULO', max_length=160, blank=True)
    cantidad_bultos = models.IntegerField(
        db_column='CANTIDAD DE BULTOS', default=0)
    unidades_por_bulto = models.IntegerField(
        db_column='UNIDADES POR BULTO', default=0)
    unidades_sueltas = models.IntegerField(
        db_column='UNIDADES SUELTAS', default=0)
    observaciones = models.TextField(
        db_column='Observaciones adicionales', blank=True)
    comprobante = models.CharField(
        db_column='COMPROBANTE', max_length=30, blank=True)
    cantidad_total = models.IntegerField(
        db_column='CANTIDAD TOTAL', default=0)
    estado_concil = models.CharField(
        db_column='ESTADO CONCILIACION', max_length=20, blank=True)
    estado_real = models.CharField(
        db_column='ESTADO REAL', max_length=40, blank=True)
    obs_cande = models.TextField(
        db_column='OBSERVACION CANDE', blank=True)
    flag_g3 = models.CharField(
        db_column='G3', max_length=30, blank=True)
    ref_bejerman = models.CharField(
        db_column='BEJERMAN', max_length=30, blank=True)

    class Meta:
        db_table = 'registro_movimiento'
        managed = False      # Supabase es dueña del schema
        verbose_name = 'Registro de movimiento'
        verbose_name_plural = 'Registros de movimientos'
        ordering = ['-creado_en_origen']

    def __str__(self):
        return f'{self.tipo} · {self.codigo} · {self.comprobante or "sin comprobante"}'
