# Barritas App — Vercel

Aplicación Flask para control de stock, compras, clientes, ventas, precios y balance.

## Deploy en Vercel

1. Subí este contenido al repositorio de GitHub.
2. En Vercel, importá el repositorio.
3. No agregues un Build Command personalizado.
4. Configurá estas variables de entorno en Vercel:
   - `SECRET_KEY`: una clave larga y aleatoria.
   - `DATABASE_URL`: URL de una base de datos PostgreSQL persistente.
5. Hacé Deploy.

Vercel detecta la función Python ubicada en `api/index.py`.

## Base de datos

El proyecto usa PostgreSQL cuando existe `DATABASE_URL` y SQLite únicamente como respaldo para desarrollo local.

**Importante:** no se incluye `database/stock.db` en GitHub. La SQLite local no debe usarse como base persistente en Vercel.

## Ejecutar localmente

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python app.py
```

Sin `DATABASE_URL`, se crea `database/stock.db` automáticamente para desarrollo local.
