# Registro de Deuda Técnica — Legacy OrderHub

> **Requisito de origen:** HU-01.1 (`docs/ANALYSIS_AND_REQUIREMENTS.md`) — auditoría
> de código, seguridad e ingeniería inversa.
>
> **Estado del documento:** describe el código tal como existe hoy en la rama de
> trabajo actual. Cada entrada se verificó leyendo el archivo citado; no se
> documenta nada por suposición.
>
> **Relación con `ARCHITECTURE.md`:** este registro es la fuente única de la
> deuda pendiente. `ARCHITECTURE.md` describe cómo está construido el sistema y
> enlaza aquí en lugar de repetir el listado, para que ambos no se
> desincronicen.

## Cómo leer este registro

Cada entrada indica **qué es**, **dónde está** (archivo:línea), **por qué es
deuda**, **qué riesgo implica** y **cuál sería la solución**. El estado es uno
de:

| Estado | Significado |
| :--- | :--- |
| 🔴 **Abierta** | Deuda vigente, sin decisión de cierre. |
| 🟡 **Diferida** | Deuda reconocida, con decisión explícita de no abordarla en esta entrega. |
| 🟡 **Parcial** | Una parte se corrigió y otra sigue abierta; ambas se detallan en la entrada. |
| ✅ **Resuelta** | Ya corregida; se conserva como registro histórico y para evitar regresiones. |

---

## Índice

| # | Deuda | Estado | Requisito |
| :--- | :--- | :--- | :--- |
| [DT-01](#dt-01--secretos-hardcodeados-en-configpy-resuelta) | Secretos hardcodeados en `config.py` | ✅ Resuelta | RNF-02.1 |
| [DT-02](#dt-02--valor-por-defecto-inseguro-de-jwt_secret_key-resuelta) | Default inseguro de `JWT_SECRET_KEY` | ✅ Resuelta | RNF-02.1 |
| [DT-03](#dt-03--columna-password-en-texto-plano-en-el-esquema) | Columna `password` en texto plano | 🟡 Diferida | RF-01.2 |
| [DT-04](#dt-04--comentario-desactualizado-en-databasepy-resuelta) | Comentario desactualizado en `database.py` | ✅ Resuelta | RNF-01.3 |
| [DT-05](#dt-05--el-panel-html-no-envía-el-token) | Panel HTML roto tras exigir token | 🟡 Diferida | RF-01.3 |
| [DT-06](#dt-06--apppy-no-es-testeable-init_db-en-el-cuerpo-de-módulo) | `app.py` no es testeable | 🟡 Diferida | RNF-01.2 |
| [DT-07](#dt-07--el-esquema-sql-está-duplicado-en-los-tests) | Esquema SQL duplicado en tests | 🔴 Abierta | RNF-01.2 |
| [DT-08](#dt-08--los-archivos-de-la-raíz-no-pasan-flake8-parcialmente-resuelta) | Archivos de la raíz no pasan flake8 | 🟡 Parcial | RNF-01.3 |
| [DT-09](#dt-09--el-esquema-no-tiene-restricciones-de-integridad-parcialmente-resuelta) | Esquema sin restricciones de integridad | 🟡 Parcial | — |
| [DT-10](#dt-10--la-notificación-de-orden-sigue-siendo-un-print) | Notificación por `print()` | 🔴 Abierta | RF-04.1 |
| [DT-11](#dt-11--inyección-sql-en-login-resuelta) | Inyección SQL en `/login` | ✅ Resuelta | RNF-02.2 |
| [DT-12](#dt-12--contraseñas-en-texto-plano-resuelta) | Contraseñas en texto plano | ✅ Resuelta | RF-01.2 |
| [DT-13](#dt-13--createorder-no-es-atómico-dos-transacciones-separadas) | `CreateOrder` no es atómico | 🔴 Abierta | RF-03.3 |
| [DT-14](#dt-14--el-catálogo-no-distingue-productos-sin-stock-ni-pagina) | `GET /products` sin filtro ni paginación | 🔴 Abierta | RF-02.1 |
| [DT-15](#dt-15--databasepy-siembra-datos-de-prueba-en-cualquier-entorno) | `init_db()` siembra datos de prueba siempre | 🔴 Abierta | RNF-02.1 |

---

## DT-01 — Secretos hardcodeados en `config.py` (RESUELTA)

**Estado:** ✅ Resuelta · **Requisito:** RNF-02.1 (*Zero Hardcoded Secrets*) · **Severidad:** Alta

**Qué era.** El módulo de configuración legado definía credenciales y una clave
secreta como literales en el código fuente: `config.py` declaraba `DB_HOST`,
`DB_USER`, `DB_PASS`, `DB_NAME` y `SECRET_KEY`. La única consumida era
`SECRET_KEY`, leída desde `app.py`; las cuatro de base de datos no se
referenciaban en ningún punto del proyecto y apuntaban a un motor que el
sistema ni siquiera usa, porque la persistencia real es SQLite.

**Qué riesgo implicaba.** Cualquiera con acceso de lectura al repositorio
—incluido el historial— obtenía la `SECRET_KEY` de Flask. Rotarla exigía un
commit y un despliegue, no un cambio de configuración.

**Cómo se resolvió.** Se eliminó `config.py` por completo y su única variable
viva se migró al patrón que el proyecto ya aplicaba en
[`src/orderhub/settings.py`](../src/orderhub/settings.py), que ahora es la
**única fuente de configuración** del sistema:

| Antes (`config.py`) | Ahora (`settings.py`) |
| :--- | :--- |
| `SECRET_KEY = "clave_secreta_super_insegura_123"` | `FLASK_SECRET_KEY` leída de `os.environ` |
| `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` | Eliminadas: no se usaban y apuntaban a un motor inexistente |
| — | `DATABASE_PATH`, antes cableada como literal en `app.py` |

Cambios concretos:

1. **`config.py` eliminado.** [`app.py`](../app.py) ya no lo importa: lee
   `settings.FLASK_SECRET_KEY` y `settings.DATABASE_PATH`.
2. **Carga de `.env`.** `settings.py` llama a `load_dotenv()` (dependencia
   `python-dotenv`, añadida a `requirements.txt`). Se usa `override=False`
   —el valor por defecto— para que en producción mande el entorno real del
   contenedor y no un `.env` olvidado en la imagen.
3. **`.env.example` versionado y `.env` ignorado.** La plantilla documenta
   todas las variables **sin ningún valor real**; `.gitignore` excluye `.env`
   y `.env.*`, con la excepción explícita `!.env.example`.
4. **`database.py` también parametrizado.** `get_db_connection()` e
   `init_db()` aceptan la ruta de la BD y, en su ausencia, la leen de
   `DATABASE_PATH`; ya no tienen `"orderhub.db"` cableado como único destino
   posible.

**Cómo se verifica que no vuelve.** No basta con la revisión manual: la suite
incluye una guarda automática en
[`tests/unit/security/test_no_hardcoded_secrets.py`](../tests/unit/security/test_no_hardcoded_secrets.py)
que falla si `config.py` reaparece, si alguno de los literales legados vuelve a
figurar en cualquier archivo fuente, si `.env.example` se rellena con valores
o si `.gitignore` deja de excluir `.env`.

**Deuda residual.** El historial de Git conserva los secretos de los commits
anteriores; están ya rotados de facto (las claves de desarrollo actuales son
otras), pero el valor antiguo sigue siendo recuperable del historial. Reescribir
el historial no se aborda aquí por ser una operación destructiva sobre una rama
compartida.

---

## DT-02 — Valor por defecto inseguro de `JWT_SECRET_KEY` (RESUELTA)

**Estado:** ✅ Resuelta · **Requisito:** RNF-02.1 · **Severidad:** Alta en despliegue, nula en desarrollo

**Qué era.** La clave de firma de los JWT caía **silenciosamente** a un valor
constante conocido (`dev-only-insecure-jwt-secret-change-me`, presente en este
repositorio) si la variable de entorno no estaba definida. El respaldo era una
decisión deliberada para que el proyecto arrancase sin configuración previa,
pero el fallo no distinguía «estoy en desarrollo» de «me desplegaron sin
configurar».

**Qué riesgo implicaba.** Un despliegue sin `JWT_SECRET_KEY` firmaba los tokens
con una clave pública: cualquiera podía **falsificar un token con rol `admin`**,
anulando RF-01.3 y RF-01.4. El sistema no daba ningún aviso.

**Cómo se resolvió.** Se introdujo la noción explícita de entorno que proponía
la entrada original. [`settings.py`](../src/orderhub/settings.py) define
`APP_ENV` (por defecto `development`) y resuelve los secretos a través de
`_required_secret()`:

```python
def _required_secret(name: str, development_fallback: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    if APP_ENV == DEVELOPMENT:
        return development_fallback
    raise MissingConfigurationError(name)
```

| `APP_ENV` | Falta `JWT_SECRET_KEY` / `FLASK_SECRET_KEY` |
| :--- | :--- |
| `development` (defecto) | Cae al respaldo: el proyecto arranca sin configurar |
| Cualquier otro (`staging`, `production`, …) | `MissingConfigurationError` **al importar el módulo**: la aplicación no llega a arrancar |

Un valor **vacío** cuenta como ausente, porque es justo lo que deja
`.env.example` al copiarse sin rellenar. El fallo es ruidoso y ocurre en el
arranque, no en la primera petición.

**Comprobado.** `APP_ENV=production python -c "import app"` aborta con el
mensaje que nombra la variable que falta y remite a `.env.example`. Los once
casos de
[`tests/unit/test_settings.py`](../tests/unit/test_settings.py) cubren ambos
entornos, el valor vacío y la precedencia del entorno sobre el respaldo.

**Nota.** Los dos respaldos de desarrollo siguen siendo literales en
`settings.py`, y eso es intencionado: no son secretos de producción sino
valores marcados como inseguros que ya **no pueden alcanzar** un despliegue
real, porque fuera de `development` el arranque falla antes de usarlos.

---

## DT-03 — Columna `password` en texto plano en el esquema

**Estado:** 🟡 Diferida · **Requisito:** RF-01.2 · **Severidad:** Media

**Qué es.** La tabla `users` conserva una columna `password` en texto plano
heredada del esquema legado, además de la columna `password_hash` que sí se usa.

**Dónde está.**
* Definición del esquema: [`database.py:52-59`](../database.py) — la columna
  `password` es la línea 55.
* Se sigue poblando con la contraseña real al sembrar los usuarios de ejemplo:
  [`database.py:88-95`](../database.py) (`'admin123'` y `'123456'`).

**Por qué es deuda.** Es **dato muerto**: ningún código del sistema la lee para
autenticar. El repositorio de usuarios consulta exclusivamente `password_hash`
([`sqlite_user_repository.py:21-24`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_user_repository.py)),
y hay un test de integración que lo comprueba de forma activa: la fixture
siembra en la columna `password` un valor **distinto** del hash
(`"texto-plano-legado"`) precisamente para que, si alguien reintrodujera una
lectura de esa columna, la autenticación fallara y el test lo delatara
([`tests/integration/conftest.py:102-105`](../tests/integration/conftest.py)).

**Qué riesgo implica.** Mientras la columna exista y se pueble, un backup
filtrado o una lectura no autorizada de la base expone las contraseñas reales
de los usuarios sembrados, aunque el flujo de login ya no las use. El riesgo no
es que el código actual las lea —no lo hace—, sino que un cambio futuro las
reintroduzca, o que el dato se filtre por la vía del almacenamiento.

**Dependencia que impide borrarla sin más.** La función
[`_backfill_password_hashes`](../database.py) (`database.py:31-43`) **lee la
columna `password`** (línea 35: `SELECT id, password FROM users WHERE
password_hash IS NULL`) para generar el hash de las filas que vienen del
esquema legado sin `password_hash`. Eliminar la columna sin retirar antes esa
migración rompería `init_db()` en cualquier base de datos preexistente.

**Cuál sería la solución.** Secuencia en dos pasos, en este orden:
1. Dejar de poblar `password` al sembrar (`database.py:88-95`) y confirmar que
   todas las bases desplegadas ya tienen `password_hash` completo.
2. Retirar `_ensure_password_hash_column` y `_backfill_password_hashes`, y
   entonces sí eliminar la columna mediante recreación de la tabla (SQLite tiene
   soporte limitado de `ALTER TABLE ... DROP COLUMN` según versión).

**Por qué se difiere.** Es una migración de esquema con datos existentes de por
medio, no una limpieza de código. El requisito RF-01.2 ya se cumple —la
autenticación real usa bcrypt— y el cambio tiene más riesgo que beneficio dentro
del alcance de esta entrega.

---

## DT-04 — Comentario desactualizado en `database.py` (RESUELTA)

**Estado:** ✅ Resuelta · **Requisito:** RNF-01.3 · **Severidad original:** Baja (documental), pero contradecía el código

**Qué era.** El docstring de `_ensure_password_hash_column` afirmaba algo falso:

> «Se conserva la columna `password` en texto plano para no romper el endpoint
> /login legado, que todavía la utiliza.»

Ese endpoint `/login` legado **ya no existe**. Fue migrado a la arquitectura
hexagonal y hoy lo sirve
[`auth_controller.py`](../src/orderhub/adapters/inbound/http/auth_controller.py),
que autentica exclusivamente contra `password_hash`.

**Qué riesgo implicaba.** Un comentario que contradice el código es peor que la
ausencia de comentario: inducía a creer que la columna era necesaria para el
login y, por tanto, a no eliminarla nunca (ver DT-03). Es el mecanismo por el
que la deuda se vuelve permanente.

**Cómo se resolvió.** El docstring de
[`_ensure_password_hash_column`](../database.py) (`database.py:18-25`) se
reescribió con la razón real y verificable: la columna `password` la necesita
`_backfill_password_hashes` como **origen** para calcular el hash de las bases
anteriores, que solo tienen la contraseña en claro. El nuevo texto además
enuncia explícitamente que ningún código de autenticación la lee y remite a
DT-03.

**Deuda residual.** Ninguna en el comentario. La columna en sí sigue existiendo:
[DT-03](#dt-03--columna-password-en-texto-plano-en-el-esquema).

---

## DT-05 — El panel HTML no envía el token

**Estado:** 🟡 Diferida (decisión explícita) · **Requisito:** RF-01.3 · **Severidad:** Media

**Qué es.** El panel de monitoreo servido en `GET /` consulta la API sin
credenciales, contra un endpoint que ahora exige token.

**Dónde está.** [`templates/index.html:37`](../templates/index.html):

```javascript
const response = await fetch('/get_all_orders_legacy');
```

La llamada no incluye cabecera `Authorization`. El endpoint destino está
protegido con `@jwt_required` desde
[`order_controller.py:69-70`](../src/orderhub/adapters/inbound/http/order_controller.py).

**Por qué es deuda.** El panel fue escrito cuando `/get_all_orders_legacy` era
público. Al implementarse RF-01.3 el contrato del endpoint cambió y el
consumidor no se actualizó.

**Qué riesgo implica.** Riesgo funcional acotado y conocido: el botón «Cargar
Órdenes desde la API» mostrará el JSON de error `401` en lugar del listado. No
hay riesgo de seguridad —el rechazo es precisamente el comportamiento
correcto— ni afecta a ningún cliente de la API, que sí envía el token.

> **Precisión sobre el alcance del fallo:** el panel **solo** hace esa llamada.
> No invoca `/create_order` ni envía `user_id` en ningún cuerpo de petición
> (verificado leyendo el archivo completo: el único `fetch` es el de la línea
> 37). El único síntoma es que el listado no carga.
>
> `GET /` en sí **sigue respondiendo 200 sin token** y así se verifica en
> [`test_full_flow_http.py:182-186`](../tests/integration/test_full_flow_http.py):
> lo que falla es la llamada AJAX posterior, no la carga de la página.

**Cuál sería la solución.** Añadir al panel un formulario de login que llame a
`POST /login`, guarde el token devuelto y lo envíe como
`Authorization: Bearer <token>` en las peticiones posteriores.

**Por qué se difiere.** **Decisión tomada:** queda fuera del alcance de esta
entrega. El alcance de esta iteración es la API y su seguridad; la interfaz web
se ajustará posteriormente.

---

## DT-06 — `app.py` no es testeable: `init_db()` en el cuerpo de módulo

**Estado:** 🟡 Diferida (decisión explícita) · **Requisito:** RNF-01.2 · **Severidad:** Media

**Qué es.** El punto de entrada ejecuta efectos secundarios al ser importado, lo
que impide que un test lo importe.

**Dónde está.** [`app.py:23`](../app.py) llama a `init_db()` directamente en el
cuerpo del módulo, y [`app.py:26`](../app.py) construye el `Container` con
`DB_PATH = "orderhub.db"` cableado en [`app.py:18`](../app.py).

**Por qué es deuda.** Importar `app.py` desde un test **escribiría en la base de
datos de desarrollo**: crearía tablas y sembraría usuarios en `orderhub.db`. No
hay forma de importar el módulo apuntando a otra base.

**Qué riesgo implica.** Dos consecuencias concretas, ambas verificables:

1. **La suite de integración replica el cableado en vez de usarlo.** La fixture
   `integration_app` en
   [`tests/integration/conftest.py:135-176`](../tests/integration/conftest.py)
   vuelve a registrar los tres blueprints y la ruta `/` a mano, y su propio
   docstring documenta el motivo: «No se importa app.py porque su cuerpo de
   módulo llama a init_db() sobre orderhub.db».
2. **Un fallo en el cableado real de `app.py` no sería detectado.** Si alguien
   olvidara registrar un blueprint, cambiara el orden de los decoradores o
   rompiera la construcción del `jwt_required` **en `app.py`**, los 123 tests
   seguirían pasando, porque prueban una copia equivalente del cableado y no el
   cableado real. Esto se refleja en la cobertura: `app.py` está al **0 %**
   (25 sentencias, 25 sin cubrir).

**Cuál sería la solución.** Refactorizar a una *application factory*:
`create_app(database_path)` que construya el `Container`, registre los
blueprints y devuelva la app, dejando en el cuerpo del módulo únicamente la
instanciación para el arranque real. La fixture de integración pasaría a llamar
a esa misma función con la ruta temporal, eliminando de paso la duplicación.

**Por qué se difiere.** **Decisión tomada:** no se aplica en esta entrega. El
requisito de cobertura ya se cumple con holgura (87 % del código fuente, 100 %
en `src/orderhub/`, frente al 80 % exigido) y modificar el punto de entrada
tiene más riesgo que beneficio en este momento.

---

## DT-07 — El esquema SQL está duplicado en los tests

**Estado:** 🔴 Abierta · **Requisito:** RNF-01.2 · **Severidad:** Media

**Qué es.** La definición de las tres tablas existe en dos lugares que deben
mantenerse sincronizados a mano.

**Dónde está.**
* Esquema real: [`database.py:50-84`](../database.py) (`init_db`).
* Copia para pruebas: [`tests/integration/conftest.py:32-54`](../tests/integration/conftest.py)
  (constante `SCHEMA`).

**Por qué es deuda.** Es consecuencia directa de DT-06: como `init_db()` tiene
`"orderhub.db"` cableado, la suite no puede reutilizarlo y se ve obligada a
replicar el esquema. El propio archivo lo reconoce en su docstring: «Es
duplicación conocida: si cambia el esquema real, hay que actualizar SCHEMA».

**Qué riesgo implica.** Si se añade una columna o una restricción en
`database.py` y no se replica en `SCHEMA`, los tests de integración seguirían
pasando contra un esquema que ya no corresponde al de producción — es decir,
darían **falsos verdes**, que es el peor modo de fallo posible en una suite de
pruebas.

> **Este riesgo ya se materializó una vez.** Al añadir `UNIQUE` a
> `users.username` ([DT-09](#dt-09--el-esquema-no-tiene-restricciones-de-integridad-parcialmente-resuelta))
> hubo que actualizar los dos sitios a mano. Si solo se hubiera tocado
> `database.py`, el test de unicidad habría fallado; si solo se hubiera tocado
> `SCHEMA`, habría pasado en verde sin que la restricción existiera de verdad
> en producción. La duplicación se sostiene únicamente por disciplina manual.

**Cuál sería la solución.** Extraer el DDL a una constante o función única (por
ejemplo `database.SCHEMA` o `database.create_schema(conn)`) parametrizada por
la conexión, e importarla desde la fixture. Se resuelve de forma natural junto
con DT-06.

---

## DT-08 — Los archivos de la raíz no pasan flake8 (PARCIALMENTE RESUELTA)

**Estado:** 🟡 Parcial — `E501` resueltos, `E402` pendientes · **Requisito:** RNF-01.3 · **Severidad:** Baja

**Qué era.** `src/orderhub/` y `tests/` cumplían flake8 y black sin un solo
hallazgo, pero los módulos legados de la raíz acumulaban **9 hallazgos**:

| Archivo:línea | Código | Detalle | Estado |
| :--- | :--- | :--- | :--- |
| `app.py:12-17` | `E402` (×6) | Imports no situados al inicio del archivo | 🔴 Pendiente |
| `app.py:58` | `E501` | Línea de 105 caracteres (comentario del HTML legado) | ✅ Resuelto |
| `database.py:89, 93, 97` | `E501` (×3) | Sentencias `INSERT` de 92–94 caracteres | ✅ Resuelto |

**Cómo se resolvieron los `E501`.** Sin usar `# noqa`:

* [`app.py`](../app.py): el comentario con el HTML legado se repartió en cuatro
  líneas de comentario, conservando el texto original como referencia histórica.
* [`database.py`](../database.py): las tres sentencias `INSERT` se partieron en
  literales de cadena adyacentes, el mismo criterio ya aplicado en
  `sqlite_order_repository.py` y `sqlite_user_repository.py`.

Estado actual verificado: `flake8 app.py database.py` reporta **exactamente
6 hallazgos, todos `E402` en `app.py:12-17`**. Eran 5 hasta la entrega 3:
`config.py` desapareció al resolverse [DT-01](#dt-01--secretos-hardcodeados-en-configpy-resuelta)
y `app.py` ganó un import más (`from orderhub import settings`), que cae bajo
el mismo `sys.path.insert` y por tanto bajo el mismo `E402`.

**Por qué los `E402` siguen abiertos — y por qué no se silencian.** No son un
descuido de formato: son **estructurales**. [`app.py:10`](../app.py) inserta
`src/` en `sys.path` y solo después puede importar `orderhub`, porque el
proyecto no está empaquetado:

```python
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from orderhub.adapters.inbound.http.auth_controller import create_auth_blueprint
```

Mover esos imports arriba rompería el arranque de la aplicación. **Decisión
tomada:** no se añade `# noqa` ni se excluye la raíz en
[`setup.cfg`](../setup.cfg), para que los seis hallazgos **sigan apareciendo en
el reporte** y la deuda permanezca visible en lugar de quedar enmascarada.

**Qué riesgo implica.** RNF-01.3 exige que «el código» cumpla PEP 8. Una futura
puerta de calidad en CI (HU-05) que ejecute flake8 sobre todo el repositorio
fallaría por estos seis hallazgos.

**Cuál sería la solución.** Empaquetar el proyecto: un `pyproject.toml` que
declare `src` como *package directory* e instalación en modo editable
(`pip install -e .`). Eso elimina la manipulación de `sys.path` y con ella los
seis `E402`, sin necesidad de excluir ni silenciar nada. Se resuelve de forma
natural junto con DT-06.

---

## DT-09 — El esquema no tiene restricciones de integridad (PARCIALMENTE RESUELTA)

**Estado:** 🟡 Parcial — unicidad de `username` resuelta, claves foráneas pendientes · **Severidad:** Media → Baja

**Qué era.** Las tres tablas se creaban sin `NOT NULL`, sin `UNIQUE` y sin
claves foráneas. La base de datos no podía garantizar por sí misma invariantes
que el sistema da por ciertos.

### ✅ Resuelto: unicidad de `users.username`

**Cuál era el riesgo concreto.** Nada impedía crear dos usuarios con el mismo
`username`. Si ocurriera,
[`find_by_username`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_user_repository.py)
usa `fetchone()` y devolvería silenciosamente el primero que retornara SQLite,
**autenticando contra un hash que podría no ser el del usuario esperado**.

**Cómo se resolvió.** En dos partes, porque una sola no bastaba:

1. **Bases nuevas** — `username TEXT UNIQUE` en el `CREATE TABLE` de
   [`database.py:77`](../database.py).
2. **Bases ya existentes** — `CREATE TABLE IF NOT EXISTS` **no modifica una
   tabla que ya existe**, así que el punto anterior por sí solo habría dejado
   `orderhub.db` sin protección. Se añadió
   [`_ensure_unique_username_index`](../database.py) (`database.py:34-52`), que
   crea un índice único sobre `username`. Un índice único impone exactamente la
   misma restricción sobre una tabla ya creada, sin recrearla ni mover datos, y
   es idempotente.

**Verificación realizada.** Tres escenarios probados:

| Escenario | Resultado |
| :--- | :--- |
| Base fresca desde cero | `UNIQUE` en el esquema; duplicado rechazado |
| Base legada preexistente (sin `UNIQUE`, sin `password_hash`) | Índice creado, backfill de hashes correcto, duplicado rechazado, `integrity_check = ok` |
| Base legada **con** duplicados | `init_db()` falla de forma explícita con `IntegrityError` |

Sobre la base real `orderhub.db`: datos y hashes idénticos antes y después,
`PRAGMA integrity_check = ok`, y la restricción activa.

**Comportamiento ante datos sucios.** Si una base heredada tuviera usernames
duplicados, la creación del índice falla ruidosamente en lugar de continuar en
silencio. Es deliberado: esos datos deben resolverse a mano, y una restricción
aplicada «a medias» sería peor que ninguna.

**Test de regresión.**
[`test_sqlite_user_repository.py`](../tests/integration/test_sqlite_user_repository.py):

* `test_no_se_pueden_guardar_dos_usuarios_con_el_mismo_username` — insertar un
  `username` repetido lanza `sqlite3.IntegrityError`.
* `test_la_unicidad_no_impide_crear_usuarios_con_username_distinto` —
  contrapartida, para comprobar que la restricción no es demasiado amplia.

El `SCHEMA` de [`tests/integration/conftest.py`](../tests/integration/conftest.py)
se actualizó en el mismo cambio para no divergir del esquema real (ver
[DT-07](#dt-07--el-esquema-sql-está-duplicado-en-los-tests)).

### 🔴 Pendiente: claves foráneas y `NOT NULL`

`orders.user_id` y `orders.product_id` **siguen sin ser claves foráneas**, y
ninguna columna obligatoria declara `NOT NULL`.

**Qué riesgo implica.** Pueden quedar órdenes apuntando a productos o usuarios
inexistentes, sin que la base lo impida. Hoy el riesgo está acotado porque
`CreateOrder` valida la existencia del producto antes de persistir y el
`user_id` proviene siempre de un token verificado, pero no hay segunda línea de
defensa en el almacenamiento.

**Cuál sería la solución.** Declarar `FOREIGN KEY` en `orders` y activar
`PRAGMA foreign_keys = ON` en
[`SQLiteConnectionFactory`](../src/orderhub/adapters/outbound/persistence/sqlite/connection.py)
—SQLite las ignora si no se activa por conexión— y añadir `NOT NULL` a las
columnas obligatorias. A diferencia del índice único, esto **sí exige recrear
las tablas**, por lo que conviene abordarlo junto con DT-03 en una única
migración de esquema.

---

## DT-10 — La notificación de orden sigue siendo un `print()`

**Estado:** 🔴 Abierta · **Requisito:** RF-04.1, RNF-05.1 · **Severidad:** Baja

**Qué es.** El aviso de «orden creada» se emite con `print()` desde el adaptador
HTTP, sin pasar por ningún puerto.

**Dónde está.** [`order_controller.py:51-56`](../src/orderhub/adapters/inbound/http/order_controller.py),
marcado en el propio código con `# TODO: reemplazar por NotifierPort cuando se
implemente RF-04.1`.

**Por qué es deuda.** Es un efecto secundario de infraestructura incrustado en
el adaptador HTTP, que debería limitarse a traducir protocolo. Además, un
`print()` no es un log estructurado.

**Qué riesgo implica.** No hay riesgo funcional ni de seguridad. Impide la
trazabilidad (RNF-05.1 pide logs JSON con marca de tiempo y severidad) y bloquea
RF-04.1, que exige emitir la notificación sin bloquear la respuesta HTTP.

**Cuál sería la solución.** Definir un `NotifierPort` en
`application/ports/`, inyectarlo en el caso de uso `CreateOrder` y proveer un
adaptador concreto. La arquitectura ya está preparada: es añadir un puerto y su
adaptador sin modificar el resto de los casos de uso.

---

## DT-11 — Inyección SQL en `/login` (RESUELTA)

**Estado:** ✅ Resuelta · **Requisito:** RNF-02.2, HU-02 · **Severidad original:** Crítica

**Qué era.** El endpoint `/login` del monolito construía la consulta
concatenando directamente los valores recibidos del cliente:

```python
f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

Visible en el commit inicial del proyecto (`git show 4c79d1d`). Una entrada como
`' OR '1'='1` en el campo `username` alteraba la lógica de la consulta y permitía
autenticarse sin credenciales válidas.

**Cómo se resolvió.** Todo el acceso a datos pasó a repositorios dedicados que
usan **exclusivamente consultas parametrizadas** con marcadores `?`, delegando
el escapado en el driver de SQLite. Verificado en los tres repositorios: no
queda ninguna concatenación de cadenas en SQL.

* [`sqlite_user_repository.py:21-24`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_user_repository.py)
* [`sqlite_product_repository.py:21-24, 33-36, 44-47`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_product_repository.py)
* [`sqlite_order_repository.py:18-28`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_order_repository.py)

**Cómo se verifica que sigue resuelta.** Hay tests automatizados que fallarían
si alguien reintrodujera la concatenación:

| Test | Qué comprueba |
| :--- | :--- |
| [`test_auth_http.py:78-80`](../tests/integration/test_auth_http.py) | `POST /login` con `username = "' OR '1'='1"` **no** autentica |
| [`test_sqlite_user_repository.py:62-66`](../tests/integration/test_sqlite_user_repository.py) | `find_by_username("' OR '1'='1")` devuelve `None` en lugar de un usuario |
| [`test_sqlite_product_repository.py:58-59`](../tests/integration/test_sqlite_product_repository.py) | Persiste el nombre `"Teclado 'Pro' de O'Brien; DROP TABLE products;--"` de forma literal y sin romper la consulta |

**Ampliación en la entrega 3 — guarda estática sobre todo el repositorio.**
Los tests anteriores prueban los tres caminos que hoy existen; no dicen nada de
una consulta nueva escrita mañana en otro archivo. Se añadió
[`tests/unit/security/test_sql_queries_are_parameterized.py`](../tests/unit/security/test_sql_queries_are_parameterized.py),
que analiza el **árbol sintáctico (AST) de todos los `.py` del proyecto** —el
código hexagonal y también el legado de la raíz— y falla si alguna cadena con
forma de SQL se construye por f-string, `+`, `%` o `.format()`.

Se comprueba que el detector funciona probándolo contra ejemplos vulnerables
conocidos, y que el descubrimiento de archivos no se ha roto (un descubrimiento
vacío haría que la guarda pasara sin analizar nada). **Resultado de la auditoría
sobre el estado actual: cero hallazgos**, tanto en `src/orderhub/` como en
`app.py` y `database.py`, cuyas sentencias `INSERT`/`UPDATE`/`SELECT` ya usan
marcadores `?`.

**Deuda residual.** Ninguna en el flujo migrado. Se conserva esta entrada como
registro histórico y como protección: cualquier revisión futura debe mantener
estos tests.

---

## DT-12 — Contraseñas en texto plano (RESUELTA)

**Estado:** ✅ Resuelta · **Requisito:** RF-01.2, HU-02 · **Severidad original:** Crítica

**Qué era.** El sistema legado almacenaba y comparaba las contraseñas en texto
plano, en la columna `users.password`.

**Cómo se resolvió.** La verificación de credenciales se realiza con **bcrypt**
a través de un puerto:

| Pieza | Ubicación |
| :--- | :--- |
| Puerto | [`application/ports/password_hasher.py`](../src/orderhub/application/ports/password_hasher.py) (`PasswordHasher`) |
| Adaptador | [`bcrypt_password_hasher.py:9-13`](../src/orderhub/adapters/outbound/security/bcrypt_password_hasher.py) (`bcrypt.checkpw`) |
| Generación del hash | [`database.py:12-15`](../database.py) (`bcrypt.hashpw` con `gensalt`) |
| Lectura | [`sqlite_user_repository.py:21-24`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_user_repository.py) — solo `password_hash` |

**Deuda residual.** La columna `password` sigue existiendo en el esquema: ver
**[DT-03](#dt-03--columna-password-en-texto-plano-en-el-esquema)**. El flujo de
autenticación ya no la usa, pero el dato permanece almacenado.

---

## DT-13 — `CreateOrder` no es atómico: dos transacciones separadas

**Estado:** 🔴 Abierta · **Requisito:** RF-03.3 · **Severidad:** Media

**Qué es.** El caso de uso que registra una orden ejecuta dos escrituras que
deberían ser una sola operación indivisible, pero que se confirman por separado
en la base de datos.

**Dónde está.** [`create_order.py:29-33`](../src/orderhub/application/use_cases/create_order.py):

```python
order = Order.create(user_id=user_id, product=product, quantity=quantity)
saved_order = self._order_repository.save(order)   # ← transacción 1

product.decrease_stock(quantity)
self._product_repository.update_stock(product)     # ← transacción 2
```

Cada repositorio abre su **propia conexión**, hace su **propio `commit`** y la
cierra:

| Operación | Abre conexión | `commit` | Cierra |
| :--- | :--- | :--- | :--- |
| `SQLiteOrderRepository.save()` | [`sqlite_order_repository.py:16`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_order_repository.py) | línea 29 | línea 32 |
| `SQLiteProductRepository.update_stock()` | [`sqlite_product_repository.py:31`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_product_repository.py) | línea 37 | línea 39 |

El origen está en [`SQLiteConnectionFactory.__call__`](../src/orderhub/adapters/outbound/persistence/sqlite/connection.py)
(`connection.py:10-13`): **cada invocación devuelve una conexión nueva**, así
que dos repositorios nunca comparten transacción, ni siquiera dentro del mismo
caso de uso.

**Por qué es deuda.** Cuando `save()` retorna, la orden ya está confirmada en
disco de forma irreversible. Si `update_stock()` falla después —fichero
bloqueado, disco lleno, proceso interrumpido entre ambas llamadas— no hay
ningún mecanismo que deshaga la primera escritura. No existe un punto en el
código donde ambas operaciones puedan revertirse juntas.

**Qué riesgo implica.** La base queda en un estado inconsistente: **la orden
existe pero el stock no se descontó**. El producto sigue anunciando unidades que
ya fueron vendidas, lo que permite sobreventa en compras posteriores. La
inconsistencia es además **silenciosa**: nada la detecta ni la registra, y solo
se manifiesta más tarde como un descuadre de inventario cuya causa ya no es
rastreable.

**Precisión sobre RF-03.3.** El requisito dice:

> «El sistema debe garantizar la consistencia transaccional: el stock solo se
> descuenta si la orden fue creada exitosamente en la base de datos.»

El código **sí cumple la mitad del enunciado**: el orden de las llamadas
garantiza que el stock nunca se descuenta antes de que la orden se haya
persistido con éxito. Lo que no cumple es la garantía recíproca —que una orden
persistida implique siempre el descuento correspondiente— y esa es justamente la
que exige una transacción real. Conviene no dar el requisito por satisfecho
leyendo solo la primera mitad.

**Por qué no es un descuido de esta iteración.** RF-03.3 pertenece a una entrega
posterior; el alcance de aquella iteración fue la seguridad de la API (RF-01.x),
la cobertura de pruebas y la calidad de código. La deuda se registró entonces
porque se detectó al auditar el flujo, no porque estuviera comprometida para
esa entrega.

**Actualización (entrega 3 — relación con RF-02.2).** Al entrar RF-02 en
alcance, esta deuda pasa a tocar un requisito ya entregado. Conviene precisar
qué cumple y qué no:

* **RF-02.2 se cumple**: el stock se descuenta y se persiste al procesar la
  orden, verificado contra la base de datos real en
  [`test_catalog_flow_http.py`](../tests/integration/test_catalog_flow_http.py).
* **RF-02.3 se cumple**: la compra se rechaza antes de escribir nada, así que
  el caso de rechazo no depende en absoluto de la atomicidad.
* **Lo que sigue sin garantizarse** es el caso de fallo entre las dos
  escrituras: orden persistida sin descuento de stock. Es exactamente el
  descuadre de inventario que describe esta entrada, y sigue exigiendo el
  patrón Unit of Work.

Es decir: RF-02 no depende de DT-13 para darse por cumplido, pero DT-13 sí
limita la fiabilidad del inventario que RF-02 introduce. Por eso su prioridad
sube tras esta entrega, aunque el requisito que la cierra (RF-03.3) siga siendo
posterior.

**Cuál sería la solución.** El patrón **Unit of Work**: una unidad de trabajo
que agrupe ambas operaciones bajo una **única transacción**, con un solo
`commit` al final o un `rollback` completo si cualquiera de los pasos falla.

En términos de esta arquitectura:

1. Definir un puerto `UnitOfWork` en `application/ports/`, con la semántica de
   un gestor de contexto: al salir sin error hace `commit`; ante una excepción,
   `rollback`.
2. Implementar el adaptador SQLite correspondiente, que abra **una sola**
   conexión y la comparta con los repositorios que participen en la unidad.
   Hoy eso exige cambiar el contrato de los repositorios, que actualmente
   obtienen su conexión de la factoría en cada método.
3. Inyectar la unidad de trabajo en `CreateOrder` desde el `Container` y
   envolver en ella las llamadas a `save()` y `update_stock()`.

El coste real no está en el caso de uso, sino en el punto 2: los tres
repositorios gestionan hoy su propio ciclo de conexión, y la unidad de trabajo
requiere invertir esa responsabilidad. Conviene abordarlo junto con la
migración a PostgreSQL (RNF-03.1), donde el manejo transaccional es un
requisito ineludible.

**Nota de alcance.** No afecta a `CreateProduct`, que realiza una única
escritura y por tanto ya es atómico por definición.

---

## DT-14 — El catálogo no distingue productos sin stock ni pagina

**Estado:** 🔴 Abierta · **Requisito:** RF-02.1 · **Severidad:** Baja

**Qué es.** `GET /products` devuelve **el catálogo completo, en una sola
respuesta y sin filtros**: incluye los productos con `stock = 0` y no admite
paginación ni búsqueda.

**Dónde está.** [`list_products.py`](../src/orderhub/application/use_cases/list_products.py)
delega en `ProductRepository.find_all()`, que en
[`sqlite_product_repository.py`](../src/orderhub/adapters/outbound/persistence/sqlite/sqlite_product_repository.py)
ejecuta un `SELECT ... FROM products ORDER BY id` sin `WHERE` ni `LIMIT`.

**Por qué es deuda.** RF-02.1 habla de «productos **disponibles**», y ahí caben
dos lecturas: todo el catálogo con su stock a la vista, o solo lo que se puede
comprar ahora. Se implementó la primera —el requisito exige mostrar «el stock
actual», lo que carece de sentido si se ocultan las filas en cero, y un
producto agotado sigue siendo información útil para el comprador y para el
administrador—, pero la decisión no está respaldada por el enunciado: es una
interpretación.

**Qué riesgo implica.** Ninguno de seguridad ni de corrección. Con dos
productos sembrados el coste es irrelevante; con un catálogo de miles de filas,
la respuesta crece sin límite y la petición se vuelve costosa en memoria y en
ancho de banda.

**Cuál sería la solución.** Confirmar la lectura de RF-02.1 con el enunciado
del curso y, si procede, añadir parámetros de consulta opcionales
(`?available=true`, `?limit=&offset=`) traducidos a argumentos del caso de uso.
El puerto lo admite sin romper nada: `find_all()` se acompañaría de un método
con criterios, sin cambiar la firma existente. La paginación conviene
abordarla junto con la migración a PostgreSQL (RNF-03.1).

---

## DT-15 — `database.py` siembra datos de prueba en cualquier entorno

**Estado:** 🔴 Abierta · **Requisito:** RNF-02.1 · **Severidad:** Media en despliegue, nula en desarrollo

**Qué es.** `init_db()` crea el esquema y, si la tabla `users` está vacía,
inserta dos usuarios de demostración con contraseñas conocidas —`admin/admin123`
y `juan/123456`— y dos productos de ejemplo. Lo hace **sin comprobar el
entorno**.

**Dónde está.** [`database.py`](../database.py), bloque
`if cursor.fetchone()[0] == 0:` dentro de `init_db()`. Se invoca desde
[`app.py`](../app.py) en cada arranque.

**Por qué es deuda.** Son credenciales conocidas y versionadas: cumplen la
misma función que un secreto hardcodeado, aunque técnicamente sean datos y no
configuración. Quedan fuera del alcance literal de RNF-02.1 —no están en un
módulo de configuración— pero comparten exactamente su riesgo.

**Qué riesgo implica.** Un despliegue contra una base vacía nace con una cuenta
`admin` de contraseña pública. Las guardas de
[DT-02](#dt-02--valor-por-defecto-inseguro-de-jwt_secret_key-resuelta) no lo
cubren: protegen la clave de firma, no el contenido sembrado en la base.

**Por qué no se resolvió en esta entrega.** La siembra es lo que hace
utilizable el proyecto en local y lo que consume la suite de integración como
datos de referencia. Quitarla sin una alternativa rompería ambos flujos, y el
alcance comprometido aquí era RF-02 y RNF-02.1/02.2. Se registra ahora porque
se detectó al auditar la configuración, no porque estuviera comprometida.

**Cuál sería la solución.** Condicionar la siembra a
`settings.APP_ENV == "development"` —la noción de entorno ya existe— y separar
la creación del esquema (siempre) de la carga de datos de ejemplo (solo en
desarrollo). Encaja de forma natural con DT-06, que ya propone sacar `init_db()`
del cuerpo de módulo de `app.py`.

---

## Deuda de alcance mayor, ya registrada en el backlog

Las siguientes carencias no se listan como entradas individuales porque no son
deuda acumulada por descuido, sino trabajo planificado de unidades posteriores
en [`ANALYSIS_AND_REQUIREMENTS.md`](ANALYSIS_AND_REQUIREMENTS.md):

| Carencia | Requisito | Unidad |
| :--- | :--- | :--- |
| Sin contenerización (`Dockerfile`, `docker-compose`) | RNF-03.1, RNF-03.2 | III |
| Sin manifiestos de Kubernetes ni HPA | RNF-03.3, RNF-03.4 | III |
| Sin pipeline de CI | RNF-04.1, RNF-04.2 | II |
| Sin análisis SAST automatizado (Bandit / SonarQube) | RNF-02.3 | I–II |
| Sin logs estructurados ni endpoint `/metrics` | RNF-05.1, RNF-05.2 | IV |
| Persistencia en SQLite en lugar de PostgreSQL | RNF-03.1 | III |
