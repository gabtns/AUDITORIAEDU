# Auditoría Edu

Dashboard Django + Supabase + PWA que lee los movimientos cargados por el
Google Form y los muestra divididos por sector con toggle "Expandir 1 mes".

```
Google Form → Sheet "SAA/DATOS"
                 │ onFormSubmit (Apps Script)
                 ▼
     Supabase REST (PostgREST)
                 │
                 ▼
         Supabase · PostgreSQL
                 ▲ SELECT (postgres role)
                 │
         Django en Render (PWA)
                 │
                 ▼
            Móvil / navegador
```

- **Ingesta**: Apps Script (en SAA) escribe directo en Supabase. Ver `apps_script/`.
- **App**: Django hosteado en Render, sólo lee. Este README.

---

## Deploy a Render (producción)

### 1. Pre-requisito: la tabla en Supabase

Si todavía no cargaste la tabla, seguí `apps_script/README.md`. Debe tener una
PK; si no, correlo en SQL Editor:

```sql
ALTER TABLE registro_movimiento ADD COLUMN IF NOT EXISTS id BIGSERIAL PRIMARY KEY;
```

### 2. Pushear el proyecto a GitHub

Un repo privado alcanza. Asegurate de que `.env` NO esté incluido (ya está en
`.gitignore`).

```bash
cd auditoria_edu
git init
git add .
git commit -m "Initial"
git branch -M main
git remote add origin https://github.com/<tu-user>/auditoria-edu.git
git push -u origin main
```

### 3. Crear el servicio en Render

1. Entrá a [render.com](https://render.com) y logueate con GitHub.
2. `New +` → `Blueprint` → elegí el repo.
3. Render detecta `render.yaml` y te muestra el servicio con las variables.
4. Las variables marcadas con un ícono de "clave" (sync:false) te las pide
   manualmente. Pegá:

   | Variable | Valor |
   |---|---|
   | `DB_PASSWORD` | la password del usuario `postgres` de Supabase |
   | `SEED_PASS_1` | `Tpaso2019` |
   | `SEED_PASS_2` | `LCastro2026` |

5. `Apply`. Render arranca el build (tarda 2–5 minutos la primera vez).

### 4. Crear los dos usuarios iniciales

En el dashboard de Render → tu servicio → `Shell` (pestaña arriba) → corré:

```bash
python manage.py seed_users
```

Devuelve `✓ Auditoria2027 creado` y `✓ LucasCastro creado`.

### 5. Probar

Entrá a `https://auditoria-edu.onrender.com` (o el subdominio que te asigne
Render). Login con `Auditoria2027` / `Tpaso2019`. Deberías ver la grilla con
los 4028 registros ya cargados.

### Limitación del plan Free

El web service free "duerme" tras 15 min sin tráfico. El primer request
después de dormir tarda ~30 segundos. Para evitarlo, pasá a Starter ($7/mes)
o pingeá cada 10 min con un cron externo (uptimerobot.com es gratis).

---

## Desarrollo local

```bash
cd auditoria_edu
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # editar con DB_PASSWORD de Supabase
python manage.py migrate
python manage.py seed_users
python manage.py runserver
```

Abrir http://localhost:8000.

---

## Rutas

| Ruta | Para qué |
|---|---|
| `/login/` | Pantalla de ingreso |
| `/dashboard/` | Grilla por sector + toggle |
| `/acerca/` | Modal "Acerca de" |
| `/logout/` | POST a cerrar sesión |
| `/admin/` | Admin de Django |

## Estructura

```
auditoria_edu/
├── build.sh                  # Render corre esto en cada deploy
├── render.yaml               # Blueprint de Render
├── .python-version           # Fija la versión de Python
├── manage.py / requirements.txt / .env.example
├── config/                   # settings, urls, wsgi
├── apps/
│   ├── accounts/             # login, logout, seed_users
│   ├── registros/            # modelo (db_column literales), dashboard
│   └── core/                 # acerca de
├── templates/
├── static/                   # CSS, PWA manifest, service worker, íconos
├── apps_script/              # Puente Sheets → Supabase (NO corre en Django)
│   ├── AuditoriaEdu.gs
│   └── README.md
└── scripts/
    └── import_bulk.py        # Carga histórica (único uso)
```
