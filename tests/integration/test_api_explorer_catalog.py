"""El catálogo del explorador de API (static/endpoints.json) refleja la API real.

La UI mantiene a mano la lista de endpoints. Estos tests impiden que se
desincronice del backend sin tocar domain/ ni application/:

- A: método y ruta del catálogo == rutas registradas en Flask.
- B: `auth` y `role` del catálogo == comportamiento observado por HTTP.

Limitación conocida (M3): se compara contra `integration_app`, que replica el
cableado de app.py. Si app.py registrara otra ruta, estos tests no lo verían.
"""

import json
import pathlib

import pytest

CATALOG_PATH = pathlib.Path(__file__).resolve().parents[2] / "static/endpoints.json"
CATALOG = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

METODOS_VALIDOS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
METODOS_IGNORADOS = {"HEAD", "OPTIONS"}
CAMPOS_OBLIGATORIOS = {
    "method",
    "path",
    "summary",
    "auth",
    "role",
    "body_example",
    "body_fields",
}
LOGIN_PATH = "/login"
VALORES_DEL_SEED = {"admin", "juan", "admin123", "123456", "texto-plano-legado"}


def _id(endpoint):
    return f"{endpoint['method']} {endpoint['path']}"


PROTEGIDOS = [e for e in CATALOG if e["auth"] and e["path"] != LOGIN_PATH]
SOLO_ADMIN = [e for e in CATALOG if e["role"] == "admin"]


def _strings(valor):
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for item in valor.values():
            yield from _strings(item)


def _call(http, endpoint, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    kwargs = {"method": endpoint["method"], "headers": headers}
    if endpoint["body_example"] is not None:
        kwargs["json"] = {}
    return http.open(endpoint["path"], **kwargs)


# --- Test A: el catálogo coincide con las rutas reales ----------------------


def test_el_catalogo_coincide_con_las_rutas_de_flask(integration_app):
    reales = {
        (metodo, regla.rule)
        for regla in integration_app.url_map.iter_rules()
        if regla.endpoint != "static" and regla.rule != "/"
        for metodo in regla.methods - METODOS_IGNORADOS
    }

    catalogo = {(e["method"], e["path"]) for e in CATALOG}

    assert catalogo == reales


# --- Test B: auth y role coinciden con el comportamiento --------------------


@pytest.mark.parametrize("endpoint", PROTEGIDOS, ids=_id)
def test_endpoint_con_auth_responde_401_sin_token(http, endpoint):
    assert _call(http, endpoint).status_code == 401


@pytest.mark.parametrize("endpoint", SOLO_ADMIN, ids=_id)
def test_endpoint_de_admin_responde_403_con_token_de_client(
    http, login, client_password, endpoint
):
    token = login("juan", client_password)

    assert _call(http, endpoint, token).status_code == 403


@pytest.mark.parametrize("endpoint", PROTEGIDOS, ids=_id)
def test_endpoint_con_auth_acepta_un_token_de_admin(
    http, login, admin_password, endpoint
):
    token = login("admin", admin_password)

    assert _call(http, endpoint, token).status_code not in (401, 403)


def test_el_catalogo_marca_como_publico_solo_el_login():
    publicos = [e["path"] for e in CATALOG if not e["auth"]]

    assert publicos == [LOGIN_PATH]


# --- Estructura del catálogo ------------------------------------------------


def test_el_catalogo_no_esta_vacio_ni_repite_endpoints():
    pares = [(e["method"], e["path"]) for e in CATALOG]

    assert pares
    assert len(pares) == len(set(pares))


@pytest.mark.parametrize("endpoint", CATALOG, ids=_id)
def test_cada_endpoint_tiene_la_estructura_esperada(endpoint):
    assert CAMPOS_OBLIGATORIOS <= set(endpoint)
    assert endpoint["method"] in METODOS_VALIDOS
    assert endpoint["path"].startswith("/")
    assert not endpoint["path"].startswith("//")
    assert isinstance(endpoint["summary"], str) and endpoint["summary"]
    assert isinstance(endpoint["auth"], bool)
    assert endpoint["role"] in (None, "admin")
    assert endpoint["body_example"] is None or isinstance(
        endpoint["body_example"], dict
    )
    assert isinstance(endpoint["body_fields"], list)


@pytest.mark.parametrize("endpoint", CATALOG, ids=_id)
def test_los_campos_del_body_estan_bien_descritos(endpoint):
    for campo in endpoint["body_fields"]:
        assert set(campo) == {"name", "type", "required", "description"}
        assert isinstance(campo["required"], bool)
        assert campo["name"] and campo["type"] and campo["description"]


@pytest.mark.parametrize("endpoint", CATALOG, ids=_id)
def test_los_campos_descritos_coinciden_con_el_ejemplo(endpoint):
    ejemplo = endpoint["body_example"]
    if ejemplo is None:
        assert endpoint["body_fields"] == []
        return

    nombres = {campo["name"] for campo in endpoint["body_fields"]}
    assert nombres == set(ejemplo)


@pytest.mark.parametrize("endpoint", CATALOG, ids=_id)
def test_el_catalogo_no_contiene_valores_del_seed(endpoint):
    textos = set(_strings(endpoint["body_example"]))

    assert not textos & VALORES_DEL_SEED


def test_el_ejemplo_de_login_no_lleva_credenciales():
    login = next(e for e in CATALOG if e["path"] == LOGIN_PATH)

    assert login["body_example"] == {"username": "", "password": ""}
