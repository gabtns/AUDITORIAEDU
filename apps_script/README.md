# Apps Script · Puente Sheets → Supabase

Este Apps Script detecta filas nuevas en el Google Sheet **SAA · DATOS** y las
escribe directo en Supabase usando la API PostgREST. **Django no interviene en
la ingesta**; sólo lee los datos ya cargados.

## Pasos en orden

### 1. Crear la tabla en Supabase (una sola vez)

En el Dashboard de Supabase (proyecto `srawajdbyfipekprtmvb`):
`SQL Editor → + New query`

Pegá y ejecutá el contenido completo de `setup_supabase.sql`.
Si todo salió bien, debería terminar en `Success. No rows returned`.

Verificá:

```sql
SELECT COUNT(*) FROM registro_movimiento;
```

Debería devolver `0`.

### 2. Obtener la service_role key

En el Dashboard: `Settings → API → Project API keys → service_role`.

Es un JWT largo que arranca con `eyJ...`. **Es una credencial que bypassa RLS
— nunca la pegues en el navegador, código versionado ni chat.** Va directo
de ese panel a Script Properties en el paso siguiente.

### 3. Cargar el Apps Script

En el Google Sheet **SAA**:
`Extensiones → Apps Script`

Borrá el `function myFunction(){}` por defecto y pegá el contenido completo
de `AuditoriaEdu.gs`. Guardá (`Ctrl+S`).
Nombre del proyecto: `Auditoria Edu Bridge`.

### 4. Configurar Script Properties

`Configuración del proyecto` (engranaje a la izquierda) → `Propiedades de
secuencia de comandos` → `Añadir propiedad`.

| Propiedad | Valor |
|---|---|
| `SUPABASE_URL` | `https://srawajdbyfipekprtmvb.supabase.co` |
| `SUPABASE_KEY` | la service_role key del paso 2 |

### 5. Probar la conexión

En el editor, seleccioná `test_ping` en el selector de función y apretá
`Ejecutar`. Primera vez: pide permisos OAuth, aceptá.

En el panel de ejecución debería mostrar:

```
HTTP 201 · (vacío)
```

Verificá en Supabase:

```sql
SELECT * FROM registro_movimiento ORDER BY creado_en DESC LIMIT 5;
```

Deberías ver una fila con `codigo = 'TEST-...'`. Eliminala si querés dejar la
tabla limpia:

```sql
DELETE FROM registro_movimiento WHERE codigo LIKE 'TEST-%' OR codigo LIKE 'PING-%';
```

### 6. Instalar el trigger

En el panel izquierdo del editor: `Activadores` (reloj) → `+ Añadir activador`
(abajo a la derecha).

**Si la hoja DATOS recibe datos desde un Google Form (lo más probable):**
- Función: `onFormSubmitTrigger`
- Deployment: `Head`
- Fuente del evento: `Desde la hoja de cálculo`
- Tipo de evento: `Al enviar un formulario`

**Si se edita a mano:**
- Función: `onChangeTrigger`
- Tipo de evento: `Al cambiar`

Guardar. Desde ahora cada fila nueva se escribe sola en Supabase.

## Operación

- Cada fila dispara un `POST` a Supabase.
- Si el comprobante+codigo+tipo ya existe en la BD, Supabase devuelve `409` y
  el log de la columna T dice `DUP`.
- Si la carga fue exitosa, Supabase devuelve `201` y el log dice `OK`.
- Si algo falló, el log dice `ERR` con el texto del error.

## Replay manual

En el editor, escribí en la caja `enviarUltimasNFilas(10)` y correlo. Reenvía
las últimas 10 filas de la hoja DATOS (saltea las que ya existen).

## Seguridad

- La service_role key **vive solamente en Script Properties** de Apps Script.
  Si se filtra, hay que rotarla en Supabase (Settings → API → `Reset
  service_role secret`), y luego volver a pegarla en Script Properties.
- **No se guarda en ningún archivo del repositorio.**
- Apps Script se ejecuta con la cuenta de Google del dueño del archivo SAA.
  Si esa cuenta se compromete, el atacante puede ver (no editar directamente)
  Script Properties. Mantené 2FA activado en la cuenta Google.

## Troubleshooting

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `HTTP 401 Invalid API key` | `SUPABASE_KEY` incorrecta | Copiar de nuevo desde Settings → API |
| `HTTP 404 relation not found` | No corriste `setup_supabase.sql` | Correrlo en SQL Editor |
| `HTTP 409` | Comprobante+código+tipo duplicado | Normal: dedup funciona |
| `HTTP 400 null value in column tipo` | Columna D vacía o distinta de env/rec | Normalizar en la hoja |
| `fetch_failed` | Sin red / URL mal escrita | Probar la URL en `curl` |
| El trigger no corre | No se instaló o se desactivó | Panel Activadores |
