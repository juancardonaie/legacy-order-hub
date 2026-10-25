"""Configuración de gunicorn para producción (se carga sola desde la raíz).

Arranque: `gunicorn app:app`

- Un solo worker: `app.py` ejecuta `init_db()` al importarse y con varios
  workers dos procesos podrían sembrar a la vez (DT-06). Además SQLite admite
  un único escritor.
- El puerto sale de PORT (lo definen las plataformas PaaS) y el host de
  APP_HOST. Por defecto escucha en todas las interfaces, porque en producción
  hay un proxy delante; para `python app.py` en local el valor es 127.0.0.1.
"""

import os

bind = (
    f"{os.environ.get('APP_HOST', '').strip() or '0.0.0.0'}:"
    f"{os.environ.get('PORT', '').strip() or '5001'}"
)
workers = 1
