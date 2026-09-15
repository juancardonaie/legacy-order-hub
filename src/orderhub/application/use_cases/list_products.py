from typing import List

from orderhub.application.ports.product_repository import ProductRepository
from orderhub.domain.entities.product import Product


class ListProducts:
    """Caso de uso: consultar el catálogo con precio y stock actual (RF-02.1).

    Devuelve entidades de dominio, no diccionarios: la forma en que el
    catálogo se serializa a JSON es una decisión del adaptador HTTP, igual
    que en ListOrders.
    """

    def __init__(self, product_repository: ProductRepository) -> None:
        self._product_repository = product_repository

    def execute(self) -> List[Product]:
        return self._product_repository.find_all()
