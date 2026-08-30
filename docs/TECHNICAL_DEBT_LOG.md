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
| [DT-01](#dt-01--secretos-hardcodeados-en-configpy) | Secretos hardcodeados en `config.py` | 🔴 Abierta | RNF-02.1 |
| [DT-02](#dt-02--valor-por-defecto-inseguro-de-jwt_secret_key) | Default inseguro de `JWT_SECRET_KEY` | 🔴 Abierta | RNF-02.1 |
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

---

## DT-01 — Secretos hardcodeados en `config.py`

**Estado:** 🔴 Abierta · **Requisito:** RNF-02.1 (*Zero Hardcoded Secrets*) · **Severidad:** Alta

**Qué es.** El módulo de configuración legado define credenciales y una clave
secreta como literales en el código fuente.

**Dónde está.** [`config.py:3-7`](../config.py) — `DB_HOST`, `DB_USER`,
`DB_PASS`, `DB_NAME` y `SECRET_KEY`. La única de esas variables que se consume
es `SECRET_KEY`, leída en [`app.py:21`](../app.py). Las cuatro de base de datos
no se referencian en ningún punto del proyecto (verificado por búsqueda: solo
aparecen en su propia definición); apuntan a un motor de base de datos que el
sistema ni siquiera usa, porque la persistencia real es SQLite.

**Por qué es deuda.** Un secreto en el código fuente queda registrado en el
historial de Git para siempre, se replica en cada clon del repositorio y no se
puede rotar sin un nuevo despliegue. Además impide tener valores distintos por
entorno (desarrollo, pruebas, producción) sin modificar el código.

**Qué riesgo implica.** Cualquiera con acceso de lectura al repositorio —
incluido el historial— obtiene la `SECRET_KEY` de Flask. Rotarla exige un
commit y un despliegue, no un cambio de configuración.

**Cuál sería la solución.** Ya existe en el proyecto el patrón correcto a
seguir: [`src/orderhub/settings.py`](../src/orderhub/settings.py) lee toda su
configuración del entorno con `os.environ.get` (líneas 18, 20 y 26) y no
contiene ningún secreto literal. La corrección es migrar `config.py` a ese
mismo esquema, cargar los valores desde un archivo `.env` excluido del control
de versiones, y eliminar las cuatro variables de base de datos que no se usan.

> Contraste directo: `settings.py` es cómo debe verse la configuración;
> `config.py` es cómo no debe verse. Conviven a propósito hasta que se complete
> la migración.

---

## DT-02 — Valor por defecto inseguro de `JWT_SECRET_KEY`

**Estado:** 🔴 Abierta · **Requisito:** RNF-02.1 · **Severidad:** Alta en despliegue, nula en desarrollo

**Qué es.** La clave de firma de los JWT cae silenciosamente a un valor
constante conocido si la variable de entorno no está definida.

**Dónde está.** [`src/orderhub/settings.py:16-18`](../src/orderhub/settings.py) —
`DEFAULT_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"`, usado como
respaldo de `os.environ.get("JWT_SECRET_KEY", ...)`.

**Por qué es deuda.** El respaldo es una decisión deliberada y razonable para
que el proyecto arranque sin configuración previa —el propio comentario en el
código lo explica—, pero el fallo es *silencioso*: no hay ninguna señal que
distinga "estoy en desarrollo" de "me desplegaron sin configurar".

**Qué riesgo implica.** Si el sistema se despliega sin definir
`JWT_SECRET_KEY`, la clave de firma es pública (está en este repositorio) y
cualquiera puede **falsificar un token con rol `admin`**, lo que anula por
completo RF-01.3 y RF-01.4. El sistema no daría ningún aviso.

**Cuál sería la solución.** Introducir una noción explícita de entorno (por
ejemplo `APP_ENV`) y hacer que la ausencia de `JWT_SECRET_KEY` sea un error
fatal al arrancar en cualquier entorno que no sea desarrollo, conservando el
respaldo solo en local.

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
| `app.py:12-16` | `E402` (×5) | Imports no situados al inicio del archivo | 🔴 Pendiente |
| `app.py:58` | `E501` | Línea de 105 caracteres (comentario del HTML legado) | ✅ Resuelto |
| `database.py:89, 93, 97` | `E501` (×3) | Sentencias `INSERT` de 92–94 caracteres | ✅ Resuelto |

**Cómo se resolvieron los `E501`.** Sin usar `# noqa`:

* [`app.py`](../app.py): el comentario con el HTML legado se repartió en cuatro
  líneas de comentario, conservando el texto original como referencia histórica.
* [`database.py`](../database.py): las tres sentencias `INSERT` se partieron en
  literales de cadena adyacentes, el mismo criterio ya aplicado en
  `sqlite_order_repository.py` y `sqlite_user_repository.py`.

Estado actual verificado: `flake8 app.py config.py database.py` reporta
**exactamente 5 hallazgos, todos `E402` en `app.py:12-16`**.

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
[`setup.cfg`](../setup.cfg), para que los cinco hallazgos **sigan apareciendo en
el reporte** y la deuda permanezca visible en lugar de quedar enmascarada.

**Qué riesgo implica.** RNF-01.3 exige que «el código» cumpla PEP 8. Una futura
puerta de calidad en CI (HU-05) que ejecute flake8 sobre todo el repositorio
fallaría por estos cinco hallazgos.

**Cuál sería la solución.** Empaquetar el proyecto: un `pyproject.toml` que
declare `src` como *package directory* e instalación en modo editable
(`pip install -e .`). Eso elimina la manipulación de `sys.path` y con ella los
cinco `E402`, sin necesidad de excluir ni silenciar nada. Se resuelve de forma
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
posterior; el alcance de esta iteración fue la seguridad de la API (RF-01.x),
la cobertura de pruebas y la calidad de código. La deuda se registra ahora
porque se detectó al auditar el flujo, no porque estuviera comprometida para
esta entrega.

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
