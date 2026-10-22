"""Guarda estática sobre la UI (static/): sin patrones XSS ni secretos.

No hay pruebas automáticas de JS (DT-17); esta guarda es la red mínima que
impide reintroducir las prácticas inseguras vetadas para el frontend.
"""

import pathlib
import re

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
STATIC_DIR = PROJECT_ROOT / "static"

UI_SUFFIXES = {".html", ".js", ".css"}

PATRONES_PROHIBIDOS = {
    "innerHTML": r"innerHTML",
    "outerHTML": r"outerHTML",
    "insertAdjacentHTML": r"insertAdjacentHTML",
    "eval()": r"\beval\s*\(",
    "new Function()": r"\bnew\s+Function\s*\(",
    "document.write": r"document\s*\.\s*write",
    "console.*": r"\bconsole\s*\.",
    "URL externa": r"https?://",
    "atributo on* en línea": r"\son[a-z]+\s*=",
    "script en línea": r"<script(?![^>]*\bsrc=)[^>]*>",
}

CREDENCIALES_DEL_SEED = ["admin123", "123456"]


def _ui_files():
    return sorted(p for p in STATIC_DIR.rglob("*") if p.suffix in UI_SUFFIXES)


def _ids(path):
    return str(path.relative_to(PROJECT_ROOT))


def test_existen_los_archivos_de_la_ui():
    nombres = {_ids(p) for p in _ui_files()}

    assert "static/index.html" in nombres
    assert "static/css/styles.css" in nombres
    for modulo in ("main", "api", "auth", "session", "ui"):
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


def test_el_detector_de_patrones_reconoce_codigo_inseguro():
    """La guarda solo sirve si de verdad detecta lo que persigue."""
    assert re.search(PATRONES_PROHIBIDOS["innerHTML"], "el.innerHTML = x")
    assert re.search(PATRONES_PROHIBIDOS["eval()"], "eval ('1')")
    assert re.search(PATRONES_PROHIBIDOS["URL externa"], "https://cdn.x/y.js")
    assert re.search(
        PATRONES_PROHIBIDOS["atributo on* en línea"], '<button onclick="f()">'
    )
    assert re.search(PATRONES_PROHIBIDOS["script en línea"], "<script>alert(1)")
    assert not re.search(
        PATRONES_PROHIBIDOS["script en línea"], '<script type="module" src="/a.js">'
    )
