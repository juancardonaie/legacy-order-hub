from orderhub.application.ports.password_hasher import PasswordHasher
from orderhub.application.ports.user_repository import UserRepository
from orderhub.domain.entities.user import User
from orderhub.domain.exceptions import InvalidCredentialsError


class AuthenticateUser:
    """Caso de uso: validar credenciales de usuario.

    Orquesta el repositorio de usuarios y el hasher de contraseñas a través
    de sus puertos. No conoce HTTP ni el algoritmo de hashing concreto.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    def execute(self, username: str, password: str) -> User:
        user = self._user_repository.find_by_username(username)
        if user is None:
            raise InvalidCredentialsError()

        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError()

        return user
