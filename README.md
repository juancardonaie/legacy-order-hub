# Legacy OrderHub - Proyecto Base de Modernización y Mantenimiento

> **Asignatura:** Actualización y Mantenimiento de Software
> **Punto de partida:** Producción Legada (v1.0.0-legacy) — *Alta Deuda Técnica*
> **Estado actual:** Arquitectura Hexagonal · Autenticación JWT · Catálogo e inventario · Interfaz web (login y explorador de API) · 516 tests
> **Cobertura de pruebas:** **100 %** en `src/orderhub/` · **99 %** del proyecto completo

---

## Descripción del Proyecto

**Legacy OrderHub** es una aplicación de gestión de usuarios, catálogo de productos y procesamiento de órdenes de compra. Nació como un monolito Flask desarrollado de forma acelerada, con un nivel crítico de **deuda técnica, vulnerabilidades de seguridad y rigidez arquitectónica**.

El rol del estudiante en este curso es asumir el mantenimiento del sistema, auditarlo, estabilizarlo y aplicar técnicas modernas (refactorización manual y asistida por IA, DevOps, contenerización, SRE y CI/CD) para transformarlo progresivamente en una **aplicación nativa de la nube (Cloud-Native) v2.0**.

> 📄 **Documentación técnica del proyecto:**
> * [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura actual, diagramas C4, flujo de autenticación y estrategia de pruebas.
> * [`docs/TECHNICAL_DEBT_LOG.md`](docs/TECHNICAL_DEBT_LOG.md) — registro de deuda técnica: qué está resuelto, qué está diferido y qué sigue abierto.
> * [`docs/ANALYSIS_AND_REQUIREMENTS.md`](docs/ANALYSIS_AND_REQUIREMENTS.md) — requisitos, historias de usuario y criterios de aceptación.

---

## Objetivos del Proyecto

### 🎯 Objetivo General
Evolucionar y modernizar la aplicación **Legacy OrderHub** desde su estado monolítico vulnerable hasta una arquitectura escalable, segura, monitoreada y desplegada mediante flujos automatizados de CI/CD.

### 🎯 Objetivos Específicos por Unidad

1. **Unidad I: Modernización Inteligente e Ingeniería Inversa**
   * Realizar auditorías de código estático y dinámico para mapear la deuda técnica y las vulnerabilidades críticas.
   * Refactorizar la arquitectura monolítica aplicando patrones de diseño (*Repository Pattern*, *Dependency Injection*) y asistencia de IA (Copilotos/Agentes).
   * Eliminar vulnerabilidades de seguridad de alto impacto (SQL Injection, exposición de secretos, contraseñas en texto plano).

2. **Unidad II: DevOps 2.0 y Calidad Automatizada**
   * Automatizar el flujo de integración continua (CI) mediante GitHub Actions / GitLab CI.
   * Implementar puertas de calidad (*Quality Gates*) para prevenir la entrada de nuevo código defectuoso.
   * Asignar métricas cuantitativas al costo de la deuda técnica y estimación de refactorización.

3. **Unidad III: Contenerización, IaC y SRE**
   * Empaquetar la aplicación y sus dependencias utilizando contenedores Docker.
   * Definir y desplegar la infraestructura en Kubernetes configurando autoescalado horizontal (HPA).
   * Gestionar secretos y variables de entorno de forma segura e independiente del código.

4. **Unidad IV: Despliegue Progresivo y Observabilidad**
   * Instrumentar la aplicación para generación de logs estructurados, métricas de rendimiento y trazas distribuidas.
   * Implementar estrategias de despliegue sin caída de servicio (*Blue/Green* o *Canary*).
   * Automatizar pruebas de regresión y de carga asistidas por IA para validar paridad funcional y resiliencia.

---

## Stack Tecnológico: punto de partida, estado actual y objetivo

| Componente | Punto de partida (v1.0 - Legado) | **Estado actual** | Estado Objetivo (v2.0 - Modernizado) |
| :--- | :--- | :--- | :--- |
| **Lenguaje / Framework** | Python / Flask Monolítico | ✅ Python 3.9 / Flask 3.1 + Arquitectura Hexagonal | Python 3.11+ / Flask o FastAPI modular |
| **Base de Datos** | SQLite (SQL concatenado) | 🟡 SQLite con consultas parametrizadas y repositorios | PostgreSQL + ORM (SQLAlchemy / Alembic) |
| **Seguridad** | Secretos *hardcoded*, contraseñas en claro | ✅ Bcrypt + JWT con expiración + roles + configuración desde `.env` (sin secretos en código) | `.env` / Vault, Hash Bcrypt/Argon2, JWT |
| **Pruebas** | Ninguna (0 % coverage) | ✅ Pytest — 516 tests, 100 % en `src/orderhub/` | Pytest + Cobertura > 80 % + Mocks de IA |
| **Calidad de código** | Sin linters | ✅ `flake8` + `black` limpios en `src/` y `tests/` | Linters + SAST en CI |
| **Infraestructura** | Ejecución local/servidor directo | ❌ Sin cambios | Docker Compose + Kubernetes (Minikube/k3s) |
| **CI / CD** | Despliegue manual | ❌ Sin cambios | GitHub Actions / GitLab CI + SonarQube |
| **Observabilidad** | `print()` en consola | ❌ Sin cambios | Prometheus + Grafana + Structured Logs (JSON) |

Leyenda: ✅ cumplido · 🟡 parcial · ❌ pendiente

---

## Deuda Técnica: diagnóstico inicial y estado actual

Estas eran las áreas críticas detectadas en la auditoría inicial (HU-01). El registro completo, con evidencia archivo:línea y plan de corrección, está en [`docs/TECHNICAL_DEBT_LOG.md`](docs/TECHNICAL_DEBT_LOG.md).

| Hallazgo inicial | Estado actual |
| :--- | :--- |
| **Inyección de SQL en `/login`** — la consulta concatenaba `username` y `password` del request. | ✅ **Resuelto.** Todas las consultas son parametrizadas (`?`). Hay tests que intentan `' OR '1'='1` y `DROP TABLE` y verifican que se neutralizan. |
| **Contraseñas en texto plano.** | ✅ **Resuelto.** Verificación con `bcrypt.checkpw` a través del puerto `PasswordHasher`. |
| **Sin sesión ni control de acceso** — cualquiera podía invocar cualquier endpoint. | ✅ **Resuelto.** JWT firmado con expiración obligatoria + autorización por rol. |
| **Código acoplado (*spaghetti*)** — `/create_order` mezclaba HTTP, cálculo de negocio y SQL en una sola función. | ✅ **Resuelto.** Separado en controlador HTTP → caso de uso → repositorio. |
| **Credenciales de BD expuestas en `config.py`.** | ✅ **Resuelto.** `config.py` fue eliminado; toda la configuración se lee del entorno en `src/orderhub/settings.py`, alimentado por un `.env` que no se versiona. Ver [DT-01](docs/TECHNICAL_DEBT_LOG.md). |
| **Falta de atomicidad transaccional** — el guardado de la orden y el descuento de stock ocurren en transacciones separadas. | 🔴 **Abierto.** Si falla el descuento de stock, la orden queda registrada igualmente (RF-03.3). Ver [DT-13](docs/TECHNICAL_DEBT_LOG.md#dt-13--createorder-no-es-atómico-dos-transacciones-separadas). |
| **Configuración rígida** — `debug=True` y puerto fijo en el código. | 🟡 **Parcial.** `debug` se controla con `APP_DEBUG` (apagado por defecto) y el servidor escucha solo en `127.0.0.1` ([DT-18](docs/TECHNICAL_DEBT_LOG.md)). El puerto `5001` sigue fijo. |

---

## API: endpoints y control de acceso

| Método | Ruta | Autenticación | Rol exigido | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | ❌ **Público** | — | Interfaz web (login y explorador de API) |
| `POST` | `/login` | ❌ **Público** | — | Valida credenciales y **devuelve un JWT** |
| `POST` | `/create_order` | ✅ Token requerido | Cualquiera autenticado | Crea una orden y descuenta stock |
| `GET` | `/get_all_orders_legacy` | ✅ Token requerido | Cualquiera autenticado | Lista todas las órdenes |
| `GET` | `/products` | ✅ Token requerido | Cualquiera autenticado | Lista el catálogo con precio y **stock actual** (RF-02.1) |
| `POST` | `/products` | ✅ Token requerido | **`admin`** | Da de alta un producto en el catálogo |

Códigos de error relevantes: **401** si falta el token, está expirado o la firma no es válida; **403** si el token es válido pero el rol no basta; **404** si el producto no existe; **400** si el stock solicitado supera el disponible (RF-02.3).

> La interfaz web vive en `static/` y es un **cliente HTTP externo** de la API: no forma parte de la arquitectura hexagonal (`src/orderhub/` no la conoce). Ofrece login y, tras iniciar sesión, un **explorador de API** ligero (tipo Swagger) para probar los endpoints sin `curl`; no hay pantallas de negocio (tablas, filtros, vistas por rol). Limitaciones: [DT-16](docs/TECHNICAL_DEBT_LOG.md) (token en `sessionStorage`) y [DT-17](docs/TECHNICAL_DEBT_LOG.md) (sin pruebas de JS).

### Cómo autenticarse

**1. Obtener un token** (usuarios de ejemplo: `admin`/`admin123` con rol `admin`, y `juan`/`123456` con rol `client`):

```bash
curl -X POST http://localhost:5001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Respuesta:

```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": { "id": 1, "username": "admin", "role": "admin" }
}
```

**2. Usar el token** en la cabecera `Authorization` de las peticiones protegidas:

```bash
TOKEN=$(curl -s -X POST http://localhost:5001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl http://localhost:5001/get_all_orders_legacy \
  -H "Authorization: Bearer $TOKEN"
```

**3. Crear un producto** (solo `admin`):

```bash
curl -X POST http://localhost:5001/products \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Teclado mecánico","price":99.99,"stock":10}'
```

**4. Consultar el catálogo** (cualquier usuario autenticado). Devuelve precio y **stock actual** de cada producto:

```bash
curl http://localhost:5001/products \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  { "id": 1, "name": "Laptop Legada", "price": 1200.0, "stock": 5 },
  { "id": 2, "name": "Mouse USB", "price": 15.5, "stock": 50 }
]
```

**5. Crear una orden** (cualquier usuario autenticado). El dueño de la orden se toma **del token**, no del cuerpo de la petición:

```bash
curl -X POST http://localhost:5001/create_order \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"product_id":1,"quantity":2}'
```

Si el stock solicitado supera el disponible, la respuesta es un **400** con el detalle del rechazo (RF-02.3), no una excepción:

```json
{
  "error": "Stock insuficiente",
  "product_id": 1,
  "requested": 99,
  "available": 5
}
```

El token caduca a los **60 minutos** por defecto. Es configurable mediante variables de entorno (`JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRATION_MINUTES`); ver `src/orderhub/settings.py`.

---

## Guía de Inicio Rápido

### Requisitos Previos
* Python 3.9 o superior.
* Git.

### Pasos para Ejecutar

**1. Clonar el repositorio:**

```bash
git clone https://github.com/tu-usuario/legacy-orderhub.git
cd legacy-orderhub
```

**2. Crear y activar un entorno virtual:**

```bash
python -m venv .venv
source .venv/bin/activate
```

En Windows: `.venv\Scripts\activate`

**3. Instalar las dependencias de ejecución:**

```bash
pip install -r requirements.txt
```

**4. Configurar el entorno** (RNF-02.1 — el proyecto no lleva ningún secreto en el código):

```bash
cp .env.example .env
```

`.env` está en `.gitignore` y **nunca debe subirse al repositorio**. En desarrollo puede dejarse tal cual: con `APP_ENV=development` la aplicación arranca usando respaldos marcados como inseguros. Fuera de desarrollo es obligatorio rellenar `JWT_SECRET_KEY` y `FLASK_SECRET_KEY`, o el arranque falla con un error explícito:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**5. Arrancar la aplicación:**

```bash
python app.py
```

La aplicación estará disponible en **http://127.0.0.1:5001** (solo loopback). La base de datos SQLite (`orderhub.db`) y sus datos de ejemplo se crean automáticamente en el primer arranque.

El modo debug de Flask (recarga y depurador de Werkzeug) está **apagado por defecto**. Para activarlo solo en tu máquina, define `APP_DEBUG=1` en `.env` o en el entorno (ver `.env.example`). No lo actives fuera de local: el depurador permite ejecutar código.

### Ejecución en producción

El servidor de `python app.py` es solo para desarrollo. En un despliegue se usa gunicorn, que lee [`gunicorn.conf.py`](gunicorn.conf.py) de la raíz:

```bash
gunicorn app:app
```

Usa **un solo worker** a propósito: `app.py` ejecuta `init_db()` al importarse (DT-06) y SQLite admite un único escritor. No subas `workers` sin resolver antes esos dos puntos.

Variables de entorno (ver `.env.example`):

| Variable | Obligatoria | Para qué |
| :--- | :--- | :--- |
| `APP_ENV` | **Sí** (`production`) | Si falta vale `development`: se siembran usuarios de demostración y se usan secretos de respaldo inseguros. |
| `JWT_SECRET_KEY`, `FLASK_SECRET_KEY` | **Sí** fuera de `development` | Sin ellas el arranque falla con `MissingConfigurationError`. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Sí, para poder entrar | Primer administrador. Se crea al arrancar si no existe; si ya existe no se toca. Se definen siempre juntas y la contraseña (máx. 72 bytes) se guarda con bcrypt. |
| `PORT` | No | Puerto. Por defecto 5001; las plataformas PaaS lo definen solas. |
| `APP_HOST` | No | Host. Con gunicorn vale `0.0.0.0` por defecto; con `python app.py`, `127.0.0.1`. Con `APP_DEBUG` solo se admite loopback. |
| `DATABASE_PATH` | No | Ruta del fichero SQLite (por defecto `orderhub.db`). |

Fuera de `development` **no se siembran** `admin`/`juan` ni los productos de demostración (DT-15): el catálogo empieza vacío y el administrador lo llena con `POST /products`.

> **SQLite y discos efímeros.** Muchos servicios PaaS borran el disco en cada despliegue o reinicio, y con él usuarios, productos y órdenes (el administrador se recrea solo desde `ADMIN_*`). Para conservar los datos hay que montar un disco persistente y apuntar `DATABASE_PATH` a él (por ejemplo `/data/orderhub.db`). Cambiar de base de datos (PostgreSQL, RNF-03) queda fuera de este paso.

### Despliegue en Render

La plataforma de despliegue es **Render** (plan gratuito, *Web Service*). No hay un `deploy.yml`: la publicación la hace Render con su **Auto-Deploy en «After CI Checks Pass»**, apoyado en el CI de GitHub Actions.

**Cómo funciona el pipeline**

1. Cada push y cada pull request hacia `develop` o `main` ejecuta [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (job «Lint y pruebas (Python 3.9)»): `flake8`, `black`, `pytest` con cobertura y la comprobación de 100 % en `src/orderhub/`.
2. Al fusionar a `main` se vuelve a ejecutar el CI sobre el commit de la fusión.
3. Render, que sigue la rama `main`, espera a que los checks de ese commit terminen y **solo despliega si todos pasan**. Si no se detecta ningún check o alguno falla, no despliega.
4. Para que nadie fusione sin CI en verde, activa en GitHub una protección de rama en `main` que exija ese check (Settings → Branches).

**Valores del panel de Render**

| Campo | Valor |
| :--- | :--- |
| Runtime | `Python 3` |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `GUNICORN_CMD_ARGS="--access-logfile -" gunicorn app:app` |
| Health Check Path | `/` |
| Auto-Deploy | `After CI Checks Pass` |
| Instance Type | `Free` |

* **Versión de Python:** la fija el archivo [`.python-version`](.python-version) (`3.9`), la misma que usa el CI. Sin él, Render usaría su versión por defecto (3.14.x para servicios nuevos), que este proyecto no ha probado. El archivo debe estar en `main` antes del primer despliegue; un test comprueba que coincide con el CI.
* **Variables de entorno:** `APP_ENV=production`, `JWT_SECRET_KEY`, `FLASK_SECRET_KEY`, `ADMIN_USERNAME` y `ADMIN_PASSWORD` (tabla de la sección anterior). No definas `PORT`: Render usa 10000 y `gunicorn.conf.py` lo respeta. Genera cada clave con `python -c "import secrets; print(secrets.token_urlsafe(48))"`; deben ser distintas entre sí.
* **Start Command:** Render inyecta `GUNICORN_CMD_ARGS="--preload --access-logfile - --bind=0.0.0.0:10000"`. Con `--preload`, gunicorn importa la app en el proceso maestro antes de lanzar el worker, y en las pruebas locales en macOS (Python 3.9) el worker terminó con `SIGSEGV` en el primer login. Anteponer `GUNICORN_CMD_ARGS="--access-logfile -"` sustituye ese valor y quita `--preload`, y funcionó. En Linux no se probó si `--preload` falla: si lo sustituyes por otro valor y todo va bien, no pierdes nada.
* **Health Check Path `/`:** devuelve la página de la interfaz (200) sin tocar la base de datos. No existe un `/health` dedicado.

**Advertencias del plan gratuito**

* **Disco efímero.** Los cambios en disco se pierden en cada despliegue, reinicio **y cuando el servicio se duerme** (el plan gratuito no admite discos persistentes). Como la base es un fichero SQLite, usuarios, productos y órdenes se pierden en cada uno de esos eventos. El administrador se recrea solo desde `ADMIN_*`; el catálogo y las órdenes, no (DT-21).
* **Se duerme tras 15 minutos sin tráfico**, y la primera petición posterior tarda en torno a un minuto. Tiene un tope de 750 horas de instancia al mes.
* **Sin `ADMIN_*` no hay ningún usuario**: la app arranca igual, pero nadie puede iniciar sesión.

**Usar la interfaz web:** abre http://127.0.0.1:5001/ , inicia sesión con el usuario de prueba del seed (`admin` o `juan`; sus contraseñas de demostración están en `database.py` y en la sección de ejemplos de `curl` de este README, nunca en la UI) y verás tu usuario, rol y hasta cuándo es válida la sesión. «Cerrar sesión» borra el token en el navegador; el servidor no revoca tokens.

**Usar el explorador de API:** tras el login aparece la lista de endpoints (método + ruta). Despliega uno, edita el body JSON si lo tiene y pulsa «Enviar»: verás el código HTTP, el tiempo en ms y la respuesta formateada.

* El token de la sesión se envía solo en los endpoints protegidos. Nunca se muestra: en la respuesta de `POST /login` el campo `token` aparece como `[oculto]`.
* La casilla «Enviar sin token» permite comprobar el `401`. Un `401` con token vigente se trata como sesión expirada y vuelve al login; un `403` o un error de red no cierran la sesión.
* La lista de endpoints vive en [`static/endpoints.json`](static/endpoints.json). Al añadir o cambiar un endpoint hay que actualizarla; `tests/integration/test_api_explorer_catalog.py` falla si se desincroniza de las rutas de Flask.

---

## Desarrollo: pruebas y calidad de código

Las herramientas de desarrollo están separadas de las de ejecución en [`requirements-dev.txt`](requirements-dev.txt) (`pytest`, `pytest-cov`, `flake8`, `black`):

```bash
pip install -r requirements-dev.txt
```

### Ejecutar las pruebas

```bash
pytest
```

Con reporte de cobertura:

```bash
pytest --cov=orderhub --cov-report=term-missing
```

La suite tiene **516 tests** organizados por capa: `tests/unit/domain/`, `tests/unit/application/`, `tests/unit/adapters/`, `tests/unit/security/` y `tests/integration/`. Los tests de integración usan Flask y SQLite reales, cada uno contra una base temporal aislada — nunca tocan `orderhub.db`.

`tests/unit/security/` contiene dos **guardas estáticas** que analizan el propio repositorio en cada ejecución: una falla si alguna consulta SQL se construye por concatenación en lugar de con parámetros (RNF-02.2), y la otra si reaparece un secreto en el código fuente o si `.env` deja de estar ignorado (RNF-02.1).

### Ejecutar los linters

```bash
flake8 src/orderhub/ tests/
black --check src/orderhub/ tests/
```

Ambos deben salir sin ningún hallazgo. La configuración de `flake8` (longitud máxima de línea: 88, compatible con `black`) está en [`setup.cfg`](setup.cfg).

> Sobre los archivos legados de la raíz: `flake8 app.py database.py` reporta **6 hallazgos `E402`** (imports no situados al inicio). Son estructurales — `app.py` debe insertar `src/` en `sys.path` antes de importar `orderhub`, porque el proyecto aún no está empaquetado. Se dejan visibles a propósito en lugar de silenciarlos con `# noqa`. Ver [DT-08](docs/TECHNICAL_DEBT_LOG.md).

---

## Reglas del Proyecto Durante el Curso

1. **Prohibido hacer push directo a la rama `main`:** todas las modificaciones deben realizarse mediante ramas (*feature branches*) e integrarse a través de Pull Requests.
2. **Cero tolerancia a secretos:** no se aceptará ningún commit que contenga claves, tokens o contraseñas en texto plano.
3. **Documentación continua:** cada refactorización o cambio arquitectónico importante debe quedar documentado en la carpeta `/docs`.

¡Bienvenido/a al proceso de modernización! El éxito de la operación depende de tu capacidad para diagnosticar, refactorizar y automatizar.
