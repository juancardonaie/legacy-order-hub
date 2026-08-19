# Arquitectura de Legacy OrderHub (Estado Actual)

> **Estado del documento:** describe el código tal como existe hoy en la rama
> `feature/crear-arquitectura-hexagonal`, después de la primera implementación
> de Arquitectura Hexagonal (Ports & Adapters). No describe un estado futuro
> ni funcionalidades planeadas.

---

## 1. Estado actual del proyecto

### 1.1 Qué era originalmente Legacy OrderHub

Legacy OrderHub nació como un monolito Flask de un solo archivo (`app.py`)
que mezclaba en los mismos handlers HTTP: enrutamiento, validación de
entrada, reglas de negocio (cálculo de totales, control de stock) y acceso
directo a SQLite mediante SQL crudo. `database.py` exponía una única función
`get_db_connection()` y `init_db()` para crear las tablas `users`,
`products` y `orders`, y sembrar datos de ejemplo.

Problemas concretos que tenía esa versión (visibles en `git show 4c79d1d`):

* **Inyección SQL en `/login`**: la consulta se construía concatenando
  directamente el `username` y el `password` recibidos en el request:
  `f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"`.
* **Contraseñas en texto plano**: la tabla `users` solo tenía la columna
  `password` y se comparaba en texto plano.
* **Secretos hardcodeados**: `config.py` define `SECRET_KEY` y credenciales
  de una base de datos (`DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`)
  directamente en el código fuente.
* **Todo en `app.py`**: los tres endpoints (`/login`, `/create_order`,
  `/get_all_orders_legacy`) tenían el control HTTP, la lógica de negocio y el
  SQL en la misma función, sin ninguna capa intermedia.
* **Cero pruebas**: no existía ningún test.

### 1.2 Qué se cambió en esta primera implementación

Se introdujo una capa nueva en `src/orderhub/` que sigue Arquitectura
Hexagonal (Ports & Adapters) y se migraron a ella **los tres endpoints que ya
existían**: `/login`, `/create_order` y `/get_all_orders_legacy`. `app.py`
dejó de contener lógica de negocio o SQL: ahora solo ensambla el `Container`
(composition root) y registra los blueprints HTTP que vienen de
`src/orderhub`.

Concretamente:

* Se creó el paquete `src/orderhub/` con capas `domain`, `application` y
  `adapters` (ver sección 2).
* Las contraseñas ahora se verifican con **bcrypt** a través de un puerto
  (`PasswordHasher`) y su adaptador (`BcryptPasswordHasher`).
* Las consultas a `users`, `products` y `orders` pasaron a ser parametrizadas
  (`?`) dentro de repositorios SQLite dedicados — ya no hay concatenación de
  strings en SQL.
* `database.py` se mantiene, pero solo para el *bootstrap* del esquema y una
  migración mínima (ver sección 3.7); ya no se importa `get_db_connection`
  desde `app.py`.
* Se agregaron **9 tests unitarios** (`tests/unit/application/`) para los
  casos de uso `AuthenticateUser` y `CreateOrder`, usando dobles en memoria
  (no tocan Flask, sqlite3 ni bcrypt).

### 1.3 Qué NO se ha implementado todavía

Esto es importante para no dar una imagen más avanzada de la que realmente
tiene el proyecto:

* **No hay interfaz gráfica de login.** Es una decisión deliberada de esta
  etapa (ver sección 4), no un olvido.
* **No hay JWT, sesiones, cookies ni middleware de autenticación.** El
  endpoint `/login` valida credenciales y responde; no emite ningún token ni
  protege otros endpoints.
* **No hay roles ni autorización.** El campo `role` del usuario se devuelve
  en la respuesta de `/login`, pero ningún endpoint lo usa para restringir
  acceso (por ejemplo, `/create_order` no verifica que el usuario sea
  `admin`).
* **La columna `password` en texto plano todavía existe** en la tabla
  `users` y `database.py` la sigue poblando al crear usuarios semilla. El
  código de la nueva arquitectura ya no la lee (`SQLiteUserRepository` solo
  hace `SELECT ... password_hash`), pero la columna no se eliminó de la
  base de datos. Ver sección 6.4.
* **`config.py` sigue teniendo secretos hardcodeados** (`SECRET_KEY`,
  credenciales de una base de datos que ni siquiera se usa). Migrarlo a
  variables de entorno es trabajo futuro explícitamente fuera del alcance de
  esta tarea.
* **Solo se migraron `AuthenticateUser` y `CreateOrder`/`ListOrders`.** No
  existen todavía casos de uso para gestión de productos más allá de
  consultarlos y descontar stock.
* **No hay capa de notificaciones (`NotifierPort`).** El aviso de "orden
  creada" sigue siendo un `print()` dentro del adaptador HTTP
  (`order_controller.py`), marcado explícitamente con un `TODO`.

---

## 2. Arquitectura actual

El proyecto usa **Arquitectura Hexagonal (Ports & Adapters)** para la parte
migrada, viviendo en `src/orderhub/`. Las tres capas están separadas por
carpeta y por dirección de dependencia: `domain` no depende de nada;
`application` depende solo de `domain`; `adapters` depende de `application`
y `domain`, nunca al revés.

`app.py`, en la raíz, actúa como **composition root**: importa el paquete
`orderhub`, construye el `Container` y registra los blueprints Flask. Es el
único lugar donde el código de infraestructura (Flask) y el de la
arquitectura hexagonal se tocan.

### 2.1 Árbol de directorios real

```text
legacy-order-hub/
├── app.py                          # Composition root: crea el Container y registra blueprints
├── config.py                       # Configuración legada (SECRET_KEY, etc.) — sin cambios
├── database.py                     # Bootstrap del esquema SQLite + migración mínima de password_hash
├── requirements.txt
├── pytest.ini                      # pythonpath = src ; testpaths = tests
├── templates/
│   └── index.html                  # Panel HTML de monitoreo servido por "/"
├── docs/
│   ├── ANALYSIS_AND_REQUIREMENTS.md
│   └── ARCHITECTURE.md             # Este documento
├── src/
│   └── orderhub/
│       ├── domain/
│       │   ├── entities/
│       │   │   ├── order.py        # Order (dataclass) + Order.create()
│       │   │   ├── product.py      # Product (dataclass) + reglas de stock/precio
│       │   │   └── user.py         # User (dataclass)
│       │   └── exceptions.py       # DomainError y subclases
│       ├── application/
│       │   ├── ports/
│       │   │   ├── order_repository.py
│       │   │   ├── product_repository.py
│       │   │   ├── user_repository.py
│       │   │   └── password_hasher.py
│       │   └── use_cases/
│       │       ├── authenticate_user.py
│       │       ├── create_order.py
│       │       └── list_orders.py
│       ├── adapters/
│       │   ├── inbound/http/
│       │   │   ├── auth_controller.py    # Blueprint de /login
│       │   │   └── order_controller.py   # Blueprint de /create_order y /get_all_orders_legacy
│       │   └── outbound/
│       │       ├── persistence/sqlite/
│       │       │   ├── connection.py               # SQLiteConnectionFactory
│       │       │   ├── sqlite_order_repository.py
│       │       │   ├── sqlite_product_repository.py
│       │       │   └── sqlite_user_repository.py
│       │       └── security/
│       │           └── bcrypt_password_hasher.py   # Adaptador de PasswordHasher
│       └── container.py            # Composition root de orderhub: instancia todo y lo inyecta
└── tests/
    └── unit/application/
        ├── test_authenticate_user.py
        └── test_create_order.py
```

No existen (todavía) carpetas como `orderhub/adapters/inbound/cli/`,
`orderhub/application/ports/notifier.py`, ni tests de integración HTTP: solo
se documenta lo que hay.

---

## 3. Explicación de cada capa

### 3.1 Domain (`src/orderhub/domain/`)

Contiene las **entidades** (`Order`, `Product`, `User`) y las
**excepciones de dominio** (`domain/exceptions.py`). Son `dataclasses`
simples con la mínima lógica de negocio que les pertenece directamente:

* `Product.has_stock_for()`, `Product.decrease_stock()` y
  `Product.price_for()` concentran las reglas de stock y precio.
* `Order.create()` calcula el total a partir del producto y valida que la
  cantidad sea mayor que cero.
* `User` es un contenedor de datos; **no** valida contraseñas (ver 3.4).

**Qué NO debería conocer el dominio** (y hoy, efectivamente, no conoce):
HTTP, Flask, SQL, sqlite3, bcrypt, ni ningún detalle de infraestructura. Se
puede confirmar leyendo los imports de `domain/entities/*.py` y
`domain/exceptions.py`: solo importan de `dataclasses`, `typing` y entre
ellos mismos.

### 3.2 Application (`src/orderhub/application/`)

#### Casos de uso (`application/use_cases/`)

Un caso de uso orquesta entidades de dominio y puertos para cumplir una
acción concreta del sistema. No conocen Flask ni SQL — dependen únicamente
de las interfaces (`ABC`) definidas en `application/ports/`. Los tres que
existen hoy:

* **`AuthenticateUser`** (`authenticate_user.py`): busca el usuario por
  username vía `UserRepository`, y si existe, verifica la contraseña vía
  `PasswordHasher`. Lanza `InvalidCredentialsError` si el usuario no existe
  o la contraseña no coincide (mismo error en ambos casos, para no filtrar
  si el username existe).
* **`CreateOrder`** (`create_order.py`): busca el producto, valida stock,
  crea la `Order` (el total lo calcula la entidad), la persiste, descuenta
  el stock y lo persiste.
* **`ListOrders`** (`list_orders.py`): delega directamente en
  `OrderRepository.find_all()`.

#### Ports (`application/ports/`)

Un **port** es una interfaz (`ABC` con métodos `@abstractmethod`) que la
capa de aplicación define porque *necesita* algo del exterior, sin saber
*cómo* se implementa. Existen para que los casos de uso dependan de una
abstracción y no de una tecnología concreta (SQLite, bcrypt, etc.), lo cual
es lo que permite testearlos con dobles en memoria (ver `tests/`) y, en
teoría, cambiar de motor de persistencia sin tocar `application/` ni
`domain/`.

En este proyecto **todos los ports son de salida (output ports)** — puertos
que la aplicación llama para pedir algo a infraestructura:

* `UserRepository.find_by_username()`
* `ProductRepository.find_by_id()` / `update_stock()`
* `OrderRepository.save()` / `find_all()`
* `PasswordHasher.verify()`

No existen **input ports** explícitos (interfaces que describan "cómo se
invoca un caso de uso desde afuera"): los adaptadores HTTP llaman
directamente a las clases de caso de uso (`AuthenticateUser`, `CreateOrder`,
`ListOrders`) como si el propio caso de uso fuera el puerto de entrada. Es
una simplificación común y razonable en proyectos de este tamaño, pero vale
aclararlo para no decir que existe algo que no existe.

### 3.3 Adapters (`src/orderhub/adapters/`)

Un **adapter** es la implementación concreta de un port (outbound) o el
punto de entrada concreto que traduce un protocolo externo a una llamada a
un caso de uso (inbound).

#### Inbound adapters (`adapters/inbound/http/`)

* **`auth_controller.py`**: expone `POST /login` como un Blueprint de
  Flask. Extrae `username`/`password` del JSON, llama a
  `AuthenticateUser.execute()`, y traduce `InvalidCredentialsError` a un
  `401`. Nunca serializa el password ni el hash en la respuesta.
* **`order_controller.py`**: expone `POST /create_order` y
  `GET /get_all_orders_legacy` como Blueprints. Traduce las excepciones de
  dominio (`ProductNotFoundError` → 404, `InsufficientStockError` /
  `InvalidQuantityError` → 400) a códigos HTTP. Las rutas conservan
  exactamente los mismos nombres que en la versión legada.

#### Outbound adapters (`adapters/outbound/`)

* **Persistencia SQLite** (`adapters/outbound/persistence/sqlite/`):
  * `connection.py` → `SQLiteConnectionFactory`: clase invocable que crea
    conexiones `sqlite3` con `row_factory = sqlite3.Row`. Se inyecta en los
    repositorios.
  * `sqlite_user_repository.py` → `SQLiteUserRepository`: implementa
    `UserRepository`. Solo hace `SELECT id, username, password_hash, role`
    — nunca lee la columna `password` en texto plano.
  * `sqlite_product_repository.py` → `SQLiteProductRepository`: implementa
    `ProductRepository`.
  * `sqlite_order_repository.py` → `SQLiteOrderRepository`: implementa
    `OrderRepository`.
  * Las tres usan siempre consultas parametrizadas (`?`), no
    concatenación de strings.
* **Seguridad** (`adapters/outbound/security/bcrypt_password_hasher.py`):
  `BcryptPasswordHasher` implementa `PasswordHasher` usando
  `bcrypt.checkpw`.

### 3.4 Dependency Injection y Repository Pattern

`src/orderhub/container.py` es el **composition root** de la arquitectura
hexagonal: es el único módulo que instancia clases concretas (los tres
repositorios SQLite, el hasher bcrypt) y las inyecta por constructor en los
casos de uso. Nada dentro de `application/` o `domain/` instancia una clase
concreta de infraestructura.

`app.py`, a su vez, instancia `Container(database_path=DB_PATH)` una sola
vez al arrancar y pasa los casos de uso ya construidos (`container.create_order`,
`container.list_orders`, `container.authenticate_user`) a los blueprints.
Esto es Dependency Injection manual (sin framework de DI): las dependencias
se construyen en un solo lugar y se pasan hacia abajo.

El **Repository Pattern** se aplica en los tres repositorios SQLite: cada
uno oculta el detalle de que la persistencia es SQLite y expone una
interfaz en términos del dominio (`find_by_id`, `save`, `find_all`, etc.),
igual que dicta el port que implementan.

---

## 4. Autenticación

### 4.1 Dónde está cada pieza

| Pieza | Ubicación |
| --- | --- |
| Caso de uso | `src/orderhub/application/use_cases/authenticate_user.py` (`AuthenticateUser`) |
| Entidad `User` | `src/orderhub/domain/entities/user.py` |
| Puerto del repositorio de usuarios | `src/orderhub/application/ports/user_repository.py` (`UserRepository`) |
| Repositorio SQLite de usuarios | `src/orderhub/adapters/outbound/persistence/sqlite/sqlite_user_repository.py` (`SQLiteUserRepository`) |
| Puerto de hashing | `src/orderhub/application/ports/password_hasher.py` (`PasswordHasher`) |
| Adaptador BCrypt | `src/orderhub/adapters/outbound/security/bcrypt_password_hasher.py` (`BcryptPasswordHasher`) |
| Controlador HTTP | `src/orderhub/adapters/inbound/http/auth_controller.py` (`create_auth_blueprint`) |
| Ensamblado (DI) | `src/orderhub/container.py` |

### 4.2 Flujo real de una petición a `/login`

```text
HTTP POST /login {username, password}
        ↓
auth_controller.login_endpoint()          (Inbound Adapter)
        ↓
AuthenticateUser.execute(username, password)   (Use Case)
        ↓
UserRepository.find_by_username(username)      (Output Port)
        ↓
SQLiteUserRepository                            (Outbound Adapter)
        ↓
SQLite: SELECT id, username, password_hash, role FROM users WHERE username = ?
        ↓
(de vuelta en el Use Case)
        ↓
PasswordHasher.verify(password, user.password_hash)   (Output Port)
        ↓
BcryptPasswordHasher.verify()  →  bcrypt.checkpw(...)   (Outbound Adapter)
        ↓
Use Case devuelve User  o  lanza InvalidCredentialsError
        ↓
auth_controller traduce a JSON 200 {status, user{id, username, role}}
                        o JSON 401 {status: error, message}
```

### 4.3 Cómo se verifica una contraseña

`AuthenticateUser.execute()` primero busca al usuario por `username`. Si no
existe, lanza `InvalidCredentialsError` de inmediato. Si existe, delega en
`PasswordHasher.verify(password, user.password_hash)`, que en producción es
`BcryptPasswordHasher`, y este llama a `bcrypt.checkpw(plain.encode(),
hash.encode())`. Si la contraseña no coincide, también se lanza
`InvalidCredentialsError` — el mismo error para "usuario no existe" y
"contraseña incorrecta", para no revelar por el mensaje si un username es
válido.

### 4.4 Cómo se almacena el password

Al arrancar, `database.py::init_db()` siembra dos usuarios de ejemplo
(`admin`/`admin123`, `juan`/`123456`) y calcula su `password_hash` con
`bcrypt.hashpw(...)` antes de insertarlos. La tabla `users` tiene columnas
`password` (texto plano, legado) y `password_hash` (bcrypt). El código de la
arquitectura hexagonal — `SQLiteUserRepository` — **solo lee
`password_hash`**; nunca lee ni compara contra la columna `password`. Esa
columna sigue existiendo en el esquema pero ya está desconectada del flujo
de autenticación real (ver sección 6.4 sobre por qué no se eliminó todavía).

### 4.5 Por qué un hash y no texto plano

Guardar la contraseña en texto plano significa que cualquiera con acceso de
lectura a la base de datos (un backup filtrado, un admin malicioso, una
inyección SQL como la que tenía el `/login` original) obtiene la contraseña
real de cada usuario, la cual muchas personas reutilizan en otros sistemas.
Un hash de bcrypt es de un solo sentido (no se puede "deshacer" para
recuperar la contraseña) y usa *salt* automático, así que ni siquiera dos
usuarios con la misma contraseña producen el mismo hash. Verificar consiste
en volver a aplicar el algoritmo con el mismo salt y comparar, nunca en
"desencriptar".

---

## 5. Decisión: no se implementó interfaz gráfica de login

**Esto es intencional, no una funcionalidad faltante de esta etapa.** El
alcance de esta primera implementación fue exclusivamente backend: dejar
`/login` funcionando de forma segura detrás de la nueva arquitectura. No se
agregó (ni se debía agregar):

* Pantalla HTML de login.
* Formularios HTML ni JavaScript de login.
* `localStorage`, JWT, cookies de sesión, ni middleware de autenticación.
* Manejo de sesión de ningún tipo.

La interfaz gráfica es un trabajo independiente que se abordará después. El
endpoint `POST /login` ya es suficiente para validar credenciales por
backend (por ejemplo, con `curl` o cualquier cliente HTTP) sin necesitar
una UI.

---

## 6. Estado de funcionalidades

| Funcionalidad | Estado | Observaciones |
| --- | --- | --- |
| Validación de usuario (búsqueda por username) | Implementada | `SQLiteUserRepository.find_by_username` |
| Verificación de password | Implementada | Bcrypt vía `PasswordHasher` / `BcryptPasswordHasher` |
| Endpoint de login (`POST /login`) | Implementado | Migrado a `auth_controller.py`, ya no usa SQL concatenado |
| Endpoint de creación de orden (`POST /create_order`) | Implementado | Migrado a `order_controller.py` |
| Endpoint de listado de órdenes (`GET /get_all_orders_legacy`) | Implementado | Nombre de ruta conservado tal cual del legado |
| Interfaz gráfica de login | No implementada | Se desarrollará posteriormente (decisión deliberada, sección 5) |
| JWT | No implementado | Fuera del alcance actual |
| Sesiones / cookies | No implementado | Fuera del alcance actual |
| Roles / autorización | No implementado | `role` se devuelve en `/login` pero ningún endpoint lo usa para restringir acceso |
| Eliminación de la columna `password` en texto plano | No implementada | La columna sigue en el esquema; el código nuevo ya no la lee (sección 6.4) |
| Migración de `config.py` a variables de entorno | No implementada | Backlog explícito de la Unidad I (`docs/ANALYSIS_AND_REQUIREMENTS.md`, HU-02.3) |
| Notificación de orden creada vía puerto dedicado (`NotifierPort`) | No implementada | Sigue siendo un `print()` en `order_controller.py`, marcado con `TODO` |
| Tests unitarios de casos de uso | Implementada | 9 tests en `tests/unit/application/`, con dobles en memoria |
| Tests de integración HTTP | No implementada | No existen tests que levanten Flask/`test_client()` todavía |

---

## 7. Cambios respecto a la arquitectura legacy

```text
ANTES (app.py monolítico)

HTTP Request
     ↓
app.py (handler)
     ├── parseo de la petición
     ├── SQL armado por concatenación de strings
     ├── reglas de negocio (cálculo de total, chequeo de stock)
     └── acceso directo a SQLite (get_db_connection)


AHORA (Hexagonal / Ports & Adapters)

HTTP Request
     ↓
Inbound Adapter (auth_controller.py / order_controller.py)
     ↓
Use Case (AuthenticateUser / CreateOrder / ListOrders)
     ↓
Output Port (UserRepository / ProductRepository / OrderRepository / PasswordHasher)
     ↓
Outbound Adapter (SQLiteUserRepository / SQLiteProductRepository / SQLiteOrderRepository / BcryptPasswordHasher)
     ↓
SQLite (orderhub.db) / bcrypt
```

`app.py` pasó de contener las tres rutas completas a ser únicamente el
composition root: construye el `Container` y registra los dos blueprints.

Esta separación mejora, de forma concreta y verificable en este código:

* **Mantenibilidad**: cambiar cómo se calcula un total (`Order.create` /
  `Product.price_for`) no requiere tocar SQL ni Flask.
* **Testabilidad**: los 9 tests en `tests/unit/application/` prueban
  `AuthenticateUser` y `CreateOrder` con repositorios en memoria, sin
  levantar Flask ni sqlite3 — se puede confirmar en el propio código de los
  tests, que documentan explícitamente esta intención.
* **Separación de responsabilidades**: cada capa tiene un tipo de cambio
  que le corresponde (SQL vs. reglas de negocio vs. protocolo HTTP), en vez
  de mezclarse en una sola función como antes.
* **Sustitución de infraestructura**: cambiar de SQLite a otro motor
  implicaría reescribir los adaptadores en `adapters/outbound/persistence/`
  sin tocar `domain/` ni `application/`, porque ambos dependen solo de los
  ports.
* **Evolución futura**: agregar, por ejemplo, un `NotifierPort` (ya
  anticipado por el `TODO` en `order_controller.py`) es agregar un port y un
  adaptador nuevos, sin modificar los casos de uso existentes más que para
  inyectar la nueva dependencia.

---

## 8. Limpieza realizada en esta tarea

### 8.1 Eliminado

| Elemento | Qué era | Por qué se eliminó |
| --- | --- | --- |
| `__pycache__/config.cpython-314.pyc` (tracked) | Bytecode compilado de `config.py`, generado por CPython | Quedó commiteado por error en el commit inicial, antes de que `.gitignore` excluyera `__pycache__`. Es un artefacto regenerable, no código fuente; ningún import lo referencia directamente. |
| `__pycache__/database.cpython-314.pyc` (tracked) | Bytecode compilado de `database.py` | Mismo caso que el anterior. |

Ambos se quitaron del índice de git (`git rm -r --cached __pycache__`) y del
disco. `.gitignore` ya contiene `__pycache__` y `/__pycache__`, así que no
volverán a aparecer como archivos rastreados. Python los regenera
automáticamente en cada ejecución; no afecta la ejecución de la app ni de
los tests (confirmado corriendo ambos después de la limpieza).

### 8.2 Candidatos a eliminación (NO eliminados — duda razonable)

| Elemento | Por qué parece innecesario | Por qué NO se eliminó |
| --- | --- | --- |
| Columna `password` (texto plano) en la tabla `users` | El código de la nueva arquitectura ya no la lee; solo usa `password_hash` | Eliminarla requiere una migración de esquema (`ALTER TABLE ... DROP COLUMN` o recreación de tabla) y afecta datos existentes; es un cambio funcional/de infraestructura, no una limpieza de archivos, y está explícitamente fuera del alcance pedido para esta tarea. Se documenta como pendiente. |
| Variables `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` en `config.py` | No se usan en ningún lugar del código (`grep` no encontró referencias fuera de la propia definición); el proyecto usa SQLite, no un servidor de base de datos | `config.py` está señalado explícitamente en el backlog del curso (`docs/ANALYSIS_AND_REQUIREMENTS.md`, HU-02.3) como algo a migrar a variables de entorno en una unidad posterior. Tocarlo ahora sería adelantar trabajo fuera del alcance de esta tarea (que es documentar y limpiar archivos, no refactorizar configuración). |
| `database.py::get_db_connection` | A primera vista podría parecer redundante con `SQLiteConnectionFactory` | Sigue siendo usada internamente por `init_db()` para el bootstrap del esquema y la migración de `password_hash`, que corren una sola vez al arrancar, antes de que exista el `Container`. No es código muerto. |

### 8.3 Explícitamente NO tocado

* **`.venv/`**: entorno virtual local del usuario. Ya está correctamente
  excluido por `.gitignore` (`.venv/`) y no está rastreado por git; borrarlo
  rompería el entorno de desarrollo activo sin ningún beneficio para el
  repositorio.
* **`orderhub.db`**: base de datos SQLite generada en tiempo de ejecución.
  Ya está excluida por `.gitignore` (`orderhub.db`) y es necesaria para que
  la app funcione localmente.
* **`.pytest_cache/`**: se autoexcluye del control de versiones (trae su
  propio `.gitignore` interno) y no aparece como archivo rastreado; no
  requiere ninguna acción.
* **`templates/index.html`**: sigue siendo servido activamente por la ruta
  `/` en `app.py` y consume `/get_all_orders_legacy` desde el navegador; no
  es código legado huérfano.
* **`config.py`**: sigue siendo usado (`SECRET_KEY`) y su limpieza de
  variables no usadas está fuera de alcance (ver 8.2).

---

## 9. Verificación realizada

* `pytest -v` → **9/9 tests pasando** (`tests/unit/application/test_authenticate_user.py`,
  `tests/unit/application/test_create_order.py`), antes y después de la
  limpieza de `__pycache__`.
* Se instanció la app Flask (`app.py`) con `test_client()` y se probó:
  * `POST /login` con credenciales válidas (`admin`/`admin123`) → `200`,
    responde `status: success` y el usuario sin password ni hash.
  * `POST /login` con contraseña incorrecta → `401`,
    `Credenciales inválidas`.
  * `GET /get_all_orders_legacy` → `200`.
  * `GET /` → `200`, sirve `templates/index.html`.
* No se detectaron imports rotos ni referencias a los archivos eliminados.
