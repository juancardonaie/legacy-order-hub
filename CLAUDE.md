# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Proyecto de curso (Actualización y Mantenimiento de Software): migra un monolito Flask + SQLite a arquitectura hexagonal. Documentación en español; mantén el idioma de código, comentarios y docs existentes (identificadores en inglés, comentarios y docs en español).

## Commands

Usa el `.venv` local (Python 3.9). Desde la raíz del repo:

```bash
pip install -r requirements.txt -r requirements-dev.txt
python app.py                        # http://127.0.0.1:5001 (solo loopback, debug apagado)
APP_DEBUG=1 python app.py            # activa recarga y depurador de Werkzeug (solo loopback)
gunicorn app:app                     # producción: 1 worker, bind APP_HOST:PORT (gunicorn.conf.py)

pytest                               # pytest.ini: pythonpath=src y la raíz, testpaths=tests
pytest tests/unit/application/test_create_order.py::test_name   # un solo test
pytest --cov=src/orderhub --cov=. --cov-report=term-missing
flake8 .                             # config en setup.cfg (88 columnas)
black --check -l 88 .
```

Estado esperado: la suite pasa completa, 100 % de cobertura en `src/orderhub/`, `black` y `flake8` limpios (los `E402` de `app.py` se toleran con `per-file-ignores` en `setup.cfg`, DT-08). No introduzcas errores nuevos. El CI (`.github/workflows/ci.yml`) ejecuta lo mismo y además exige 100 % en `src/orderhub/`.

Configuración por `.env` (copiar de `.env.example`). Con `APP_ENV=development` hay secretos de respaldo inseguros; fuera de él, faltar `JWT_SECRET_KEY` o `FLASK_SECRET_KEY` aborta el arranque. `APP_DEBUG`, `PORT`, `APP_HOST`, `ADMIN_USERNAME` y `ADMIN_PASSWORD` los leen `app.py`/`gunicorn.conf.py`/`database.py`, no `settings.py`. En cambio `RATE_LIMIT_ENABLED`, `RATE_LIMIT_{LOGIN,USERS,GLOBAL}_{MAX,WINDOW}` y `TRUSTED_PROXY_HOPS` sí los lee `settings.py` (por defecto 30/60, 30/60, 300/60 y 0; un valor inválido aborta el arranque). Los contadores son en memoria y solo valen con un worker (DT-23); con `TRUSTED_PROXY_HOPS=0` se ignora `X-Forwarded-For`.

## Architecture

Hexagonal en `src/orderhub/`. Las dependencias apuntan hacia adentro:

- `domain/` (entidades `Product`, `Order`, `User` y excepciones) y `application/` (puertos ABC en `ports/`, casos de uso en `use_cases/`) **no importan** Flask, sqlite3, bcrypt, jwt, os ni dotenv, ni `adapters`/`container`. Mantén esa pureza.
- `adapters/inbound/http/`: blueprints Flask, `jwt_required` y `require_role`. Traducen excepciones de dominio a JSON + código HTTP; las excepciones de dominio no conocen HTTP. El rate limit vive aquí y está partido a propósito: `rate_limiter.py` es el limitador puro (**sin Flask**, lo construye el `Container`) y `rate_limiting.py` es la parte HTTP (clave IP/usuario, `429` + `Retry-After`, límite global, `ProxyFix`). `install_rate_limiting(...)` es el único cableado y lo llaman `app.py` y `tests/integration/conftest.py`.
- `adapters/outbound/`: repositorios SQLite (SQL siempre parametrizado con `?`), `BcryptPasswordHasher`, `JWTTokenService` (único módulo que importa `jwt`).
- `container.py` es el único sitio que instancia clases concretas e inyecta por constructor. La composición queda repartida: `jwt_required` se construye en `app.py` (depende de Flask, el `Container` no debe conocerlo) y los blueprints se registran allí.

Raíz del repo (legado, fuera del hexágono): `app.py` (arranque; añade `src/` a `sys.path`, llama a `init_db()` **al importar**, DT-06; los tests lo importan sustituyendo `database.init_db` por un espía, ver `tests/integration/test_app_entrypoint.py`) y `database.py` (esquema, migraciones mínimas, seed de demostración **solo con `APP_ENV=development`** y primer admin desde `ADMIN_USERNAME`/`ADMIN_PASSWORD`, idempotente). La suite de integración replica el cableado de `app.py` en `tests/integration/conftest.py` (`integration_app`).

Autenticación: `AuthenticateUser` valida con el hasher; el **controller** emite el JWT. El rol viaja dentro del token (claim `role`): cambiar el rol en la BD exige nuevo login. `POST /create_order` toma `user_id` del token, nunca del body. `POST /products` y `POST /users` exigen rol `admin`; el resto, token válido (`/login` y `/` son públicos). No hay registro público: solo un admin crea usuarios, con `role` `client` (por defecto) o `admin` en el body, validado en el dominio. En `POST /users` el orden de decoradores es `@jwt_required`, límite por `user_id`, `@require_role("admin")`. Los formatos de error no son uniformes (`{status, message}` vs `{error}`).

### UI (`static/`)

Cliente HTTP externo, **fuera del hexágono**: `src/orderhub/` no la importa. HTML + JS vanilla (módulos ES), sin Node ni build ni recursos externos; Flask sirve `GET /` y `/static/*`. Contiene el login, un explorador de API tipo Swagger ligero alimentado por `static/endpoints.json` (solo lista los endpoints cuyo `role` es `null` o el de la sesión) y, solo para `admin`, el formulario «Crear usuario» (`static/js/users.js` sobre `request()` de `api.js`). Ocultar por rol es comodidad; la seguridad es el `403` del backend.

Reglas que las guardas de `tests/unit/security/test_static_ui_safety.py` hacen cumplir:

- Todo dato dinámico con `textContent`; prohibidos `innerHTML`, `eval`, `console.*`, URLs `http(s)://`, atributos `on*` y scripts en línea; CSP `default-src 'self'`.
- `fetch(` solo en `static/js/api.js`; `sessionStorage`/`localStorage` solo en `static/js/session.js`.
- Ninguna credencial del seed en `static/`.

Al añadir o cambiar un endpoint, actualiza `static/endpoints.json`: `tests/integration/test_api_explorer_catalog.py` falla si no coincide con `url_map` de Flask, con `auth` (401 sin token) o con `role` (403 con token de `client`). El JS no se ejecuta en la suite (DT-17).

## CI/CD y despliegue

- CI: `.github/workflows/ci.yml` en push y PR hacia `develop` y `main` (Python 3.9; `flake8`, `black`, `pytest` con cobertura y 100 % en `src/orderhub/`). No hay `deploy.yml`.
- Despliegue: **Render** (plan gratuito), rama `main`, Auto-Deploy «After CI Checks Pass». Build `pip install -r requirements.txt`; start `GUNICORN_CMD_ARGS="--access-logfile -" gunicorn app:app`; health check `/`. Valores y variables en la sección «Despliegue en Render» del README.
- `.python-version` (`3.9`) debe coincidir con el CI; `tests/unit/test_deploy_config.py` lo comprueba. Gunicorn va con **un solo worker**: `init_db()` corre al importar `app.py` y SQLite admite un único escritor.
- Render inyecta `GUNICORN_CMD_ARGS` con `--preload`; en macOS con Python 3.9 eso mató al worker (`SIGSEGV`) en el primer login. Por eso el start command lo sustituye. Efímero: el disco del plan gratuito se borra al redesplegar, reiniciar o dormirse (DT-21).

## Convenciones del repo

- Cambios de backend para la UI van en `app.py` o como caso de uso + controller con test; nunca en `domain/` ni `application/`.
- Flujo de ramas `feature → develop → main`. No hagas commit ni push si el usuario no lo pide.
- La deuda técnica está en `docs/TECHNICAL_DEBT_LOG.md` (DT-01…DT-22): consúltala antes de tocar código que podría estar ya decidido o diferido. `docs/ARCHITECTURE.md` describe el diseño; `docs/ANALYSIS_AND_REQUIREMENTS.md` tiene los requisitos RF/RNF. Si cambian cifras de tests o cobertura, actualiza README y ARCHITECTURE (§6, §8.1, §9).
- `orderhub.db` y `.env` no se versionan. El seed (`admin`/`juan`) solo corre si `users` está vacía.
