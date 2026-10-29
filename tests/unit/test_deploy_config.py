"""Coherencia de la configuración de despliegue y de CI.

Render lee `.python-version` y `requirements.txt` desde `main`, y el CI declara
su propia versión de Python. Si estos archivos se desalinean, el despliegue
usaría una versión distinta de la que prueban los tests.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

DEV_TOOLS = {"pytest", "pytest-cov", "flake8", "black"}


def _requirement_names():
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    return [line.split("==")[0].strip().lower() for line in lines if line.strip()]


def _ci_python_version():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    match = re.search(r'python-version:\s*"([^"]+)"', workflow)
    assert match, "ci.yml ya no declara python-version"
    return match.group(1)


def test_python_version_es_una_sola_linea_con_una_version():
    contenido = (ROOT / ".python-version").read_text(encoding="utf-8")

    assert re.fullmatch(r"\d+\.\d+(\.\d+)?\n?", contenido)


def test_python_version_coincide_con_el_python_del_ci():
    pin = (ROOT / ".python-version").read_text(encoding="utf-8").strip()

    assert pin == _ci_python_version()


def test_requirements_incluye_gunicorn_para_el_comando_de_inicio():
    assert "gunicorn" in _requirement_names()


def test_requirements_no_mezcla_herramientas_de_desarrollo():
    assert not DEV_TOOLS & set(_requirement_names())


def test_requirements_tiene_todas_las_versiones_fijadas():
    lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()

    for line in filter(str.strip, lines):
        assert re.fullmatch(r"[A-Za-z0-9_.\-]+==[0-9][^\s]*", line), line
