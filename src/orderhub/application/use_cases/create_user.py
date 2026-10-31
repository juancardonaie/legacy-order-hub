from orderhub.application.ports.password_hasher import PasswordHasher
from orderhub.application.ports.user_repository import UserRepository
from orderhub.domain.entities.user import (
    ROLE_CLIENT,
    User,
    validate_password,
    validate_role,
    validate_username,
)
from orderhub.domain.exceptions import UsernameAlreadyExistsError


class CreateUser:
    """Caso de uso: dar de alta un usuario.

    Operación administrativa. Quién puede invocarla es una decisión del
    adaptador HTTP; este caso de uso solo orquesta dominio y puertos. El rol se
    valida en el dominio (solo "admin" o "client").
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    def execute(self, username: str, password: str, role: str = ROLE_CLIENT) -> User:
        # Primero las validaciones baratas: bcrypt es lento a propósito y no
        # debe gastarse con entradas inválidas ni con usernames repetidos.
        validate_username(username)
        validate_role(role)
        validate_password(password)

        if self._user_repository.find_by_username(username) is not None:
            raise UsernameAlreadyExistsError(username)

        user = User.create(
            username=username,
            password_hash=self._password_hasher.hash(password),
            role=role,
        )
        # Si otra alta ganó la carrera entre la consulta y este guardado, el
        # repositorio lanza UsernameAlreadyExistsError.
        return self._user_repository.add(user)
