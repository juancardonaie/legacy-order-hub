from orderhub.application.ports.product_repository import ProductRepository
from orderhub.domain.entities.product import Product


class CreateProduct:
    """Caso de uso: dar de alta un producto en el catálogo.

    Operación administrativa (RF-01.4). Quién puede invocarla es una decisión
    del adaptador HTTP, que es donde vive el concepto de "usuario autenticado";
    este caso de uso solo orquesta dominio y puerto.
    """

    def __init__(self, product_repository: ProductRepository) -> None:
        self._product_repository = product_repository

    def execute(self, name: str, price: float, stock: int = 0) -> Product:
        product = Product.create(name=name, price=price, stock=stock)
        return self._product_repository.save(product)
