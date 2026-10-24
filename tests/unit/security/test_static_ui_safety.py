"""Guarda estática sobre la UI (static/): sin patrones XSS ni secretos.

No hay pruebas automáticas de JS (DT-17); esta guarda es la red mínima que
impide reintroducir las prácticas inseguras vetadas para el frontend.
"""

import pathlib
import re

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
STATIC_DIR = PROJECT_ROOT / "static"

UI_SUFFIXES = {".html", ".js", ".css", ".json"}

PATRONES_PROHIBIDOS = {
    "innerHTML": r"innerHTML",
    "outerHTML": r"outerHTML",
    "insertAdjacentHTML": r"insertAdjacentHTML",
    "eval()": r"\beval\s*\(",
    "new Function()": r"\bnew\s+Function\s*\(",
    "document.write": r"document\s*\.\s*write",
    "console.*": r"\bconsole\s*\.",
    "URL externa": r"https?://",
    # Solo dentro de una etiqueta HTML: así no salta con variables JS como
    # `once = 1` (falso positivo del patrón anterior).
    "atributo on* en línea": r"<[^<>]*\son[a-z]+\s*=",
    "setAttribute on*": r"setAttribute\(\s*[\"']on",
    "document.cookie": r"document\s*\.\s*cookie",
    "javascript:": r"javascript\s*:",
    "srcdoc": r"srcdoc",
    "script en línea": r"<script(?![^>]*\bsrc=)[^>]*>",
}

CREDENCIALES_DEL_SEED = ["admin123", "123456"]

# Solo un módulo puede hablar con la red y solo uno con el almacenamiento.
PATRON_FETCH = r"\bfetch\s*\("
PATRON_ALMACENAMIENTO = r"\b(sessionStorage|localStorage)\b"


def _ui_files():
    return sorted(p for p in STATIC_DIR.rglob("*") if p.suffix in UI_SUFFIXES)


def _ids(path):
    return str(path.relative_to(PROJECT_ROOT))


def test_existen_los_archivos_de_la_ui():
    nombres = {_ids(p) for p in _ui_files()}

    assert "static/index.html" in nombres
    assert "static/css/styles.css" in nombres
    assert "static/endpoints.json" in nombres
    for modulo in ("main", "api", "auth", "session", "ui", "explorer"):
        assert f"static/js/{modulo}.js" in nombres


def test_el_panel_legado_fue_reemplazado():
    assert not (PROJECT_ROOT / "templates" / "index.html").exists()


def test_el_html_carga_el_js_como_modulo_es():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    assert 'type="module"' in html


def test_el_html_declara_una_politica_csp_de_mismo_origen():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    assert "Content-Security-Policy" in html
    assert "default-src 'self'" in html


@pytest.mark.parametrize("path", _ui_files(), ids=_ids)
@pytest.mark.parametrize("nombre", PATRONES_PROHIBIDOS)
def test_la_ui_no_contiene_patrones_prohibidos(path, nombre):
    contenido = path.read_text(encoding="utf-8")

    assert not re.search(PATRONES_PROHIBIDOS[nombre], contenido), (
        f"{_ids(path)} contiene '{nombre}'. La UI debe pintar con textContent, "
        "sin recursos externos y sin registrar datos de sesión."
    )


@pytest.mark.parametrize("path", _ui_files(), ids=_ids)
@pytest.mark.parametrize("credencial", CREDENCIALES_DEL_SEED)
def test_la_ui_no_contiene_credenciales_del_seed(path, credencial):
    assert credencial not in path.read_text(encoding="utf-8")


def _js_files_except(nombre):
    return [p for p in _ui_files() if p.suffix == ".js" and p.name != nombre]


@pytest.mark.parametrize("path", _js_files_except("api.js"), ids=_ids)
def test_fetch_solo_se_usa_en_api_js(path):
    contenido = path.read_text(encoding="utf-8")

    assert not re.search(PATRON_FETCH, contenido), (
        f"{_ids(path)} llama a fetch(). Toda petición HTTP pasa por api.js, "
        "que es el único sitio que adjunta el token."
    )


@pytest.mark.parametrize("path", _js_files_except("session.js"), ids=_ids)
def test_el_almacenamiento_solo_se_usa_en_session_js(path):
    contenido = path.read_text(encoding="utf-8")

    assert not re.search(PATRON_ALMACENAMIENTO, contenido), (
        f"{_ids(path)} usa sessionStorage/localStorage. El token solo se "
        "guarda y lee desde session.js."
    )


def test_api_js_y_session_js_son_los_que_usan_red_y_almacenamiento():
    api = (STATIC_DIR / "js" / "api.js").read_text(encoding="utf-8")
    session = (STATIC_DIR / "js" / "session.js").read_text(encoding="utf-8")

    assert re.search(PATRON_FETCH, api)
    assert re.search(PATRON_ALMACENAMIENTO, session)


def test_el_detector_de_patrones_reconoce_codigo_inseguro():
    """La guarda solo sirve si de verdad detecta lo que persigue."""
    assert re.search(PATRONES_PROHIBIDOS["innerHTML"], "el.innerHTML = x")
    assert re.search(PATRONES_PROHIBIDOS["eval()"], "eval ('1')")
    assert re.search(PATRONES_PROHIBIDOS["URL externa"], "https://cdn.x/y.js")
    assert re.search(
        PATRONES_PROHIBIDOS["atributo on* en línea"], '<button onclick="f()">'
    )
    assert re.search(
        PATRONES_PROHIBIDOS["atributo on* en línea"],
        '<input type="text" onfocus=f()>',
    )
    assert not re.search(
        PATRONES_PROHIBIDOS["atributo on* en línea"], "const once = 1;"
    )
    assert re.search(
        PATRONES_PROHIBIDOS["setAttribute on*"], 'el.setAttribute("onclick", x)'
    )
    assert re.search(PATRONES_PROHIBIDOS["document.cookie"], "document.cookie = x")
    assert re.search(PATRONES_PROHIBIDOS["javascript:"], '<a href="javascript:f()">')
    assert re.search(PATRONES_PROHIBIDOS["srcdoc"], "frame.srcdoc = x")
    assert re.search(PATRON_FETCH, "await fetch (url)")
    assert re.search(PATRON_ALMACENAMIENTO, "window.localStorage.setItem(a, b)")
    assert re.search(PATRONES_PROHIBIDOS["script en línea"], "<script>alert(1)")
    assert not re.search(
        PATRONES_PROHIBIDOS["script en línea"], '<script type="module" src="/a.js">'
    )
