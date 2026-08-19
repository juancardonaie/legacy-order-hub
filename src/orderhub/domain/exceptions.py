"""Excepciones del dominio.

No conocen HTTP ni base de datos: los adaptadores son los responsables de
traducirlas al protocolo que corresponda.
"""


class DomainError(Exception):
    """Error base de las reglas de negocio."""


class ProductNotFoundError(DomainError):
    def __init__(self, product_id):
        super().__init__("Producto no encontrado")
        self.product_id = product_id


class InsufficientStockError(DomainError):
    def __init__(self, product_id, requested, available):
        super().__init__("Stock insuficiente")
        self.product_id = product_id
        self.requested = requested
        self.available = available


class InvalidQuantityError(DomainError):
    def __init__(self, quantity):
        super().__init__("La cantidad debe ser mayor que cero")
        self.quantity = quantity


class InvalidCredentialsError(DomainError):
    def __init__(self):
        super().__init__("Credenciales inválidas")
