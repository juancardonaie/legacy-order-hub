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


class InvalidProductNameError(DomainError):
    def __init__(self, name):
        super().__init__("El nombre del producto no puede estar vacío")
        self.name = name


class InvalidProductPriceError(DomainError):
    def __init__(self, price):
        super().__init__("El precio debe ser mayor que cero")
        self.price = price


class InvalidStockError(DomainError):
    def __init__(self, stock):
        super().__init__("El stock no puede ser negativo")
        self.stock = stock


class InvalidUsernameError(DomainError):
    def __init__(self, username):
        super().__init__(
            "El nombre de usuario debe tener entre 3 y 32 caracteres "
            "y solo puede usar minúsculas, dígitos, '.', '_' y '-'"
        )
        self.username = username


class InvalidPasswordError(DomainError):
    """Contraseña que incumple la política. No guarda la contraseña: el mensaje
    describe la regla incumplida y nada más, para que no acabe en un log."""


class InvalidRoleError(DomainError):
    def __init__(self, role):
        super().__init__("El rol debe ser 'admin' o 'client'")
        self.role = role


class UsernameAlreadyExistsError(DomainError):
    def __init__(self, username):
        super().__init__("El nombre de usuario ya existe")
        self.username = username
