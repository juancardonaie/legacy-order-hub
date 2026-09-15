"""Guarda automática contra SQL Injection (RNF-02.2, OWASP A03).

No prueba comportamiento: analiza el árbol sintáctico de TODO el código
Python del proyecto —el hexagonal y el legado de la raíz— y falla si alguna
cadena con aspecto de SQL se construye por interpolación (f-string, `%`, `+`
o `.format()`) en vez de con parámetros `?`.

Por qué un test y no una revisión manual: la revisión se hace una vez y la
regresión llega en el commit siguiente. Esto convierte RNF-02.2 en algo que
la suite verifica en cada ejecución.

Nota: la concatenación implícita de literales adyacentes (`"SELECT ..." "
FROM ..."`) es un único literal para el intérprete y no interpola nada, así
que no la detecta ni debe detectarla; el proyecto la usa para respetar el
límite de 88 columnas.
"""

import ast
import pathlib
import re

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]

EXCLUDED_DIRS = {".venv", "venv", ".git", "__pycache__", ".pytest_cache"}

# Este mismo archivo contiene literales SQL de ejemplo dentro de los casos de
# prueba; se excluye para no acusarse a sí mismo.
EXCLUDED_FILES = {pathlib.Path(__file__).resolve()}

SQL_PATTERN = re.compile(
    r"\b(SELECT|INSERT\s+INTO|UPDATE|DELETE\s+FROM|DROP\s+TABLE|"
    r"CREATE\s+TABLE|ALTER\s+TABLE|WHERE|VALUES)\b",
    re.IGNORECASE,
)


def _python_files():
    for path in sorted(PROJECT_ROOT.rglob("*.py")):
        if EXCLUDED_DIRS & set(path.parts):
            continue
        if path.resolve() in EXCLUDED_FILES:
            continue
        yield path


def _looks_like_sql(node) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(SQL_PATTERN.search(node.value))
    )


class _InterpolatedSQLVisitor(ast.NodeVisitor):
    """Recoge los nodos donde una cadena SQL se construye dinámicamente."""

    def __init__(self) -> None:
        self.findings = []

    def _report(self, node, how: str) -> None:
        self.findings.append((node.lineno, how))

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        tiene_sql = any(_looks_like_sql(part) for part in node.values)
        tiene_interpolacion = any(
            isinstance(part, ast.FormattedValue) for part in node.values
        )
        if tiene_sql and tiene_interpolacion:
            self._report(node, "f-string")
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Add, ast.Mod)) and (
            _looks_like_sql(node.left) or _looks_like_sql(node.right)
        ):
            operador = "+" if isinstance(node.op, ast.Add) else "%"
            self._report(node, f"concatenación con '{operador}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
            and _looks_like_sql(node.func.value)
        ):
            self._report(node, ".format()")
        self.generic_visit(node)


@pytest.mark.parametrize(
    "path", list(_python_files()), ids=lambda p: str(p.relative_to(PROJECT_ROOT))
)
def test_ninguna_consulta_sql_se_construye_por_interpolacion(path):
    visitor = _InterpolatedSQLVisitor()
    visitor.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))

    assert not visitor.findings, "\n".join(
        f"{path.relative_to(PROJECT_ROOT)}:{line} — SQL construido por {how}. "
        "Usa una consulta parametrizada con '?'."
        for line, how in visitor.findings
    )


def test_el_detector_reconoce_una_f_string_vulnerable():
    """El guarda solo sirve si de verdad detecta el patrón que persigue."""
    codigo = "q = f\"SELECT * FROM users WHERE username = '{username}'\""

    visitor = _InterpolatedSQLVisitor()
    visitor.visit(ast.parse(codigo))

    assert [how for _, how in visitor.findings] == ["f-string"]


@pytest.mark.parametrize(
    "codigo, esperado",
    [
        ('q = "SELECT * FROM users WHERE id = " + user_id', "concatenación con '+'"),
        ('q = "SELECT * FROM users WHERE id = %s" % user_id', "concatenación con '%'"),
        ('q = "SELECT * FROM users WHERE id = {}".format(user_id)', ".format()"),
    ],
)
def test_el_detector_reconoce_las_demas_formas_de_interpolacion(codigo, esperado):
    visitor = _InterpolatedSQLVisitor()
    visitor.visit(ast.parse(codigo))

    assert [how for _, how in visitor.findings] == [esperado]


def test_el_detector_no_marca_una_consulta_parametrizada():
    """Ni la parametrizada ni la concatenación implícita de literales."""
    codigo = (
        "cursor.execute(\n"
        '    "SELECT id, name, price, stock FROM products "\n'
        '    "WHERE id = ?",\n'
        "    (product_id,),\n"
        ")\n"
    )

    visitor = _InterpolatedSQLVisitor()
    visitor.visit(ast.parse(codigo))

    assert visitor.findings == []


def test_el_detector_ignora_una_f_string_que_no_es_sql():
    codigo = 'print(f"Notificando la orden {order_id}")'

    visitor = _InterpolatedSQLVisitor()
    visitor.visit(ast.parse(codigo))

    assert visitor.findings == []


def test_el_proyecto_tiene_archivos_que_analizar():
    """Si el descubrimiento se rompiera, la guarda pasaría en vacío."""
    analizados = list(_python_files())

    assert len(analizados) > 20
    assert any(p.name == "database.py" for p in analizados)
    assert any(p.name == "sqlite_user_repository.py" for p in analizados)
