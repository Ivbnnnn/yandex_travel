from sqlalchemy.exc import IntegrityError

from ..db import User
from ..exceptions import UserAlreadyExistsError, UserNotFoundError
from ..repositories import UserRepository
from ..schemas import UserCreate, UserCreateRoute, UserUpdate
from ..security import PasswordService


def is_email_conflict(exc: IntegrityError) -> bool:
    """Recognize only the email constraint, not every integrity error."""
    original = exc.orig
    for error in (original, getattr(original, "__cause__", None)):
        if getattr(error, "constraint_name", None) == "uq_users_email":
            return True
        if getattr(getattr(error, "diag", None), "constraint_name", None) == "uq_users_email":
            return True
    # SQLite is used in the portable test suite.
    return "UNIQUE constraint failed: users.email" in str(original)


class UserService:
    def __init__(self, users: UserRepository, passwords: PasswordService):
        self.users = users
        self.session = users.session
        self.passwords = passwords

    async def register(self, data: UserCreateRoute) -> User:
        password_hash = await self.passwords.hash(data.password)
        try:
            async with self.session.begin():
                if await self.users.get_user_by_email(str(data.email)):
                    raise UserAlreadyExistsError()
                return await self.users.insert(
                    UserCreate(
                        **data.model_dump(exclude={"password"}),
                        password_hash=password_hash,
                    )
                )
        except IntegrityError as exc:
            if is_email_conflict(exc):
                raise UserAlreadyExistsError() from exc
            raise

    async def profile(self, user_id: int) -> User:
        async with self.session.begin():
            user = await self.users.read(user_id)
            if user is None:
                raise UserNotFoundError()
            return user

    async def update(self, user_id: int, data: UserUpdate) -> User:
        try:
            async with self.session.begin():
                user = await self.users.update(user_id, data)
                if user is None:
                    raise UserNotFoundError()
                return user
        except IntegrityError as exc:
            if is_email_conflict(exc):
                raise UserAlreadyExistsError() from exc
            raise

    async def delete(self, user_id: int) -> None:
        async with self.session.begin():
            if await self.users.delete(user_id) is None:
                raise UserNotFoundError()
