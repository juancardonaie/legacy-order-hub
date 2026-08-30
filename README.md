# Legacy OrderHub - Proyecto Base de Modernización y Mantenimiento

> **Asignatura:** Actualización y Mantenimiento de Software
> **Punto de partida:** Producción Legada (v1.0.0-legacy) — *Alta Deuda Técnica*
> **Estado actual:** Arquitectura Hexagonal · Autenticación JWT · 125 tests
> **Cobertura de pruebas:** **100 %** en `src/orderhub/` · **86 %** del código fuente del proyecto

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
| **Seguridad** | Secretos *hardcoded*, contraseñas en claro | 🟡 Bcrypt + JWT con expiración + roles; `config.py` aún con secretos | `.env` / Vault, Hash Bcrypt/Argon2, JWT |
| **Pruebas** | Ninguna (0 % coverage) | ✅ Pytest — 125 tests, 100 % en `src/orderhub/` | Pytest + Cobertura > 80 % + Mocks de IA |
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
| **Credenciales de BD expuestas en `config.py`.** | 🔴 **Abierto.** Ver [DT-01](docs/TECHNICAL_DEBT_LOG.md). El patrón correcto ya existe en `src/orderhub/settings.py`, que lee del entorno. |
| **Falta de atomicidad transaccional** — el guardado de la orden y el descuento de stock ocurren en transacciones separadas. | 🔴 **Abierto.** Si falla el descuento de stock, la orden queda registrada igualmente (RF-03.3). Ver [DT-13](docs/TECHNICAL_DEBT_LOG.md#dt-13--createorder-no-es-atómico-dos-transacciones-separadas). |
| **Configuración rígida** — `debug=True` y puerto fijo en el código. | 🔴 **Abierto.** `app.py` sigue con `debug=True` y `port=5001` cableados. |

---

## API: endpoints y control de acceso

| Método | Ruta | Autenticación | Rol exigido | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | ❌ **Público** | — | Panel HTML de monitoreo |
| `POST` | `/login` | ❌ **Público** | — | Valida credenciales y **devuelve un JWT** |
| `POST` | `/create_order` | ✅ Token requerido | Cualquiera autenticado | Crea una orden y descuenta stock |
| `GET` | `/get_all_orders_legacy` | ✅ Token requerido | Cualquiera autenticado | Lista todas las órdenes |
| `POST` | `/products` | ✅ Token requerido | **`admin`** | Da de alta un producto en el catálogo |

Códigos de error relevantes: **401** si falta el token, está expirado o la firma no es válida; **403** si el token es válido pero el rol no basta.

> ⚠️ El panel HTML (`GET /`) carga correctamente, pero su botón «Cargar Órdenes» no envía la cabecera `Authorization` y por tanto recibe un `401`. Es una limitación conocida y documentada: ver [DT-05](docs/TECHNICAL_DEBT_LOG.md).

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

**4. Crear una orden** (cualquier usuario autenticado). El dueño de la orden se toma **del token**, no del cuerpo de la petición:

```bash
curl -X POST http://localhost:5001/create_order \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"product_id":1,"quantity":2}'
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

**4. Arrancar la aplicación:**

```bash
python app.py
```

La API estará disponible en **http://localhost:5001**. La base de datos SQLite (`orderhub.db`) y sus datos de ejemplo se crean automáticamente en el primer arranque.

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

La suite tiene **125 tests** organizados por capa: `tests/unit/domain/`, `tests/unit/application/`, `tests/unit/adapters/` y `tests/integration/`. Los tests de integración usan Flask y SQLite reales, cada uno contra una base temporal aislada — nunca tocan `orderhub.db`.

### Ejecutar los linters

```bash
flake8 src/orderhub/ tests/
black --check src/orderhub/ tests/
```

Ambos deben salir sin ningún hallazgo. La configuración de `flake8` (longitud máxima de línea: 88, compatible con `black`) está en [`setup.cfg`](setup.cfg).

> Sobre los archivos legados de la raíz: `flake8 app.py config.py database.py` reporta **5 hallazgos `E402`** (imports no situados al inicio). Son estructurales — `app.py` debe insertar `src/` en `sys.path` antes de importar `orderhub`, porque el proyecto aún no está empaquetado. Se dejan visibles a propósito en lugar de silenciarlos con `# noqa`. Ver [DT-08](docs/TECHNICAL_DEBT_LOG.md).

---

## Reglas del Proyecto Durante el Curso

1. **Prohibido hacer push directo a la rama `main`:** todas las modificaciones deben realizarse mediante ramas (*feature branches*) e integrarse a través de Pull Requests.
2. **Cero tolerancia a secretos:** no se aceptará ningún commit que contenga claves, tokens o contraseñas en texto plano.
3. **Documentación continua:** cada refactorización o cambio arquitectónico importante debe quedar documentado en la carpeta `/docs`.

¡Bienvenido/a al proceso de modernización! El éxito de la operación depende de tu capacidad para diagnosticar, refactorizar y automatizar.
