"""Guarda automática contra secretos en código fuente (RNF-02.1).

Comprueba tres cosas sobre el árbol del proyecto:

1. El antiguo `config.py` de la raíz, que declaraba `DB_PASS` y `SECRET_KEY`
   como literales, ya no existe (DT-01 resuelta).
2. Ninguno de sus literales sobrevive copiado en otro archivo.
3. `.env` está excluido del control de versiones y `.env.example` existe y no
   trae valores rellenados.
"""

import pathlib
import re

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]

EXCLUDED_DIRS = {".venv", "venv", ".git", "__pycache__", ".pytest_cache"}

EXCLUDED_FILES = {pathlib.Path(__file__).resolve()}

# Literales exactos que vivían en el config.py legado.
SECRETOS_LEGADOS = [
    "admin1234_super_secret",
    "clave_secreta_super_insegura_123",
]


def _source_files():
    for pattern in ("*.py", "*.html", "*.cfg", "*.ini", "*.txt"):
        for path in sorted(PROJECT_ROOT.rglob(pattern)):
            if EXCLUDED_DIRS & set(path.parts):
                continue
            if path.resolve() in EXCLUDED_FILES:
                continue
            yield path


def test_el_configpy_legado_ya_no_existe():
    assert not (PROJECT_ROOT / "config.py").exists(), (
        "config.py volvió a aparecer: la configuración debe leerse del entorno "
        "en src/orderhub/settings.py. Ver DT-01."
    )


@pytest.mark.parametrize("secreto", SECRETOS_LEGADOS)
def test_ningun_secreto_legado_sigue_en_el_codigo(secreto):
    culpables = [
        str(path.relative_to(PROJECT_ROOT))
        for path in _source_files()
        if secreto in path.read_text(encoding="utf-8", errors="ignore")
    ]

    assert culpables == [], f"El secreto legado sigue presente en: {culpables}"


def test_existe_la_plantilla_env_example():
    contenido = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    for variable in (
        "APP_ENV",
        "JWT_SECRET_KEY",
        "FLASK_SECRET_KEY",
        "DATABASE_PATH",
    ):
        assert variable in contenido


def test_la_plantilla_no_trae_valores_de_secretos_rellenados():
    """`.env.example` documenta qué variables hay, nunca con qué valores."""
    contenido = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    for linea in contenido.splitlines():
        if re.match(r"^\s*(JWT_SECRET_KEY|FLASK_SECRET_KEY)\s*=", linea):
            assert (
                linea.split("=", 1)[1].strip() == ""
            ), f"'{linea}' trae un valor: .env.example debe quedar vacío."


def test_el_gitignore_excluye_el_env_real_pero_no_la_plantilla():
    lineas = [
        linea.strip()
        for linea in (PROJECT_ROOT / ".gitignore")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert ".env" in lineas
    assert "!.env.example" in lineas
