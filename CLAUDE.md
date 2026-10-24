# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Proyecto de curso (Actualización y Mantenimiento de Software): migra un monolito Flask + SQLite a arquitectura hexagonal. Documentación en español; mantén el idioma de código, comentarios y docs existentes (identificadores en inglés, comentarios y docs en español).

## Commands

Usa el `.venv` local (Python 3.9). Desde la raíz del repo:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python app.py                        # http://127.0.0.1:5001 (solo loopback, debug apagado)
APP_DEBUG=1 python app.py            # activa recarga y depurador de Werkzeug

pytest                               # pytest.ini: pythonpath=src, testpaths=tests
pytest tests/unit/application/test_create_order.py::test_name   # un solo test
pytest --cov=src/orderhub --cov=. --cov-report=term-missing
flake8 .                             # config en setup.cfg (88 columnas)
black --check -l 88 .
```

Estado esperado: la suite pasa completa, 100 % de cobertura en `src/orderhub/`, `black` limpio y `flake8` con solo 6 × `E402` en `app.py` (DT-08, conocidos). No introduzcas errores nuevos.

Configuración por `.env` (copiar de `.env.example`). Con `APP_ENV=development` hay secretos de respaldo inseguros; fuera de él, faltar `JWT_SECRET_KEY` o `FLASK_SECRET_KEY` aborta el arranque. `APP_DEBUG` lo lee `app.py`, no `settings.py`.

## Architecture

Hexagonal en `src/orderhub/`. Las dependencias apuntan hacia adentro:

- `domain/` (entidades `Product`, `Order`, `User` y excepciones) y `application/` (puertos ABC en `ports/`, casos de uso en `use_cases/`) **no importan** Flask, sqlite3, bcrypt, jwt, os ni dotenv, ni `adapters`/`container`. Mantén esa pureza.
- `adapters/inbound/http/`: blueprints Flask, `jwt_required` y `require_role`. Traducen excepciones de dominio a JSON + código HTTP; las excepciones de dominio no conocen HTTP.
- `adapters/outbound/`: repositorios SQLite (SQL siempre parametrizado con `?`), `BcryptPasswordHasher`, `JWTTokenService` (único módulo que importa `jwt`).
- `container.py` es el único sitio que instancia clases concretas e inyecta por constructor. La composición queda repartida: `jwt_required` se construye en `app.py` (depende de Flask, el `Container` no debe conocerlo) y los blueprints se registran allí.

Raíz del repo (legado, fuera del hexágono): `app.py` (arranque; añade `src/` a `sys.path`, llama a `init_db()` **al importar**, por lo que no se puede importar en tests, DT-06) y `database.py` (esquema, migraciones mínimas y seed). La suite de integración replica el cableado de `app.py` en `tests/integration/conftest.py` (`integration_app`).

Autenticación: `AuthenticateUser` valida con el hasher; el **controller** emite el JWT. El rol viaja dentro del token (claim `role`): cambiar el rol en la BD exige nuevo login. `POST /create_order` toma `user_id` del token, nunca del body. Solo `POST /products` exige rol `admin`; el resto, token válido (`/login` y `/` son públicos). Los formatos de error no son uniformes (`{status, message}` vs `{error}`).

### UI (`static/`)

Cliente HTTP externo, **fuera del hexágono**: `src/orderhub/` no la importa. HTML + JS vanilla (módulos ES), sin Node ni build ni recursos externos; Flask sirve `GET /` y `/static/*`. Contiene el login y un explorador de API tipo Swagger ligero alimentado por `static/endpoints.json`.

Reglas que las guardas de `tests/unit/security/test_static_ui_safety.py` hacen cumplir:

- Todo dato dinámico con `textContent`; prohibidos `innerHTML`, `eval`, `console.*`, URLs `http(s)://`, atributos `on*` y scripts en línea; CSP `default-src 'self'`.
- `fetch(` solo en `static/js/api.js`; `sessionStorage`/`localStorage` solo en `static/js/session.js`.
- Ninguna credencial del seed en `static/`.

Al añadir o cambiar un endpoint, actualiza `static/endpoints.json`: `tests/integration/test_api_explorer_catalog.py` falla si no coincide con `url_map` de Flask, con `auth` (401 sin token) o con `role` (403 con token de `client`). El JS no se ejecuta en la suite (DT-17).

## Convenciones del repo

- Cambios de backend para la UI van en `app.py` o como caso de uso + controller con test; nunca en `domain/` ni `application/`.
- Flujo de ramas `feature → develop → main`. No hagas commit ni push si el usuario no lo pide.
- La deuda técnica está en `docs/TECHNICAL_DEBT_LOG.md` (DT-01…DT-20): consúltala antes de tocar código que podría estar ya decidido o diferido. `docs/ARCHITECTURE.md` describe el diseño; `docs/ANALYSIS_AND_REQUIREMENTS.md` tiene los requisitos RF/RNF. Si cambian cifras de tests o cobertura, actualiza README y ARCHITECTURE (§6, §8.1, §9).
- `orderhub.db` y `.env` no se versionan. El seed (`admin`/`juan`) solo corre si `users` está vacía.
