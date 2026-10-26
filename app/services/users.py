from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from ..errors import AuthenticationError, ConflictError
from ..security import PasswordService, TokenService, token_hash
from .base import BaseService, public


class UserService(BaseService):
    async def profile(self, user_id):
        async with self.uow_factory() as uow:
            return public(await uow.users.get(user_id))

    async def update(self, user_id, data):
        try:
            async with self.uow_factory() as uow:
                user = await uow.users.get(user_id, lock=True)
                self.patch(user, data, nullable=("phone",))
                await uow.commit()
                return public(user)
        except IntegrityError as exc:
            raise ConflictError("Email is already registered") from exc

    async def deactivate(self, user_id):
        async with self.uow_factory() as uow:
            user = await uow.users.get(user_id, lock=True)
            user.is_active = False
            await uow.sessions_repo.revoke_all(user_id)
            await uow.commit()


class AuthService(BaseService):
    def __init__(self, uow_factory, settings, tokens: TokenService, passwords: PasswordService):
        super().__init__(uow_factory, settings)
        self.tokens, self.passwords = tokens, passwords

    async def register(self, data):
        hashed = await self.passwords.hash(data.password)
        try:
            async with self.uow_factory() as uow:
                if await uow.users.by_email(data.email):
                    raise ConflictError("Email is already registered")
                user = await uow.users.add(
                    **data.model_dump(exclude={"password"}), password_hash=hashed
                )
                await uow.commit()
                return public(user)
        except IntegrityError as exc:
            raise ConflictError("Email is already registered") from exc

    async def login(self, data):
        async with self.uow_factory() as uow:
            user = await uow.users.by_email(data.email, lock=True)
            stored = user.password_hash if user and user.is_active else None
            if not await self.passwords.verify(data.password, stored):
                raise AuthenticationError("Invalid email or password")
            sid = uuid4()
            pair = self.tokens.pair(user.id, sid)
            claims = self.tokens.verify(pair["refresh_token"], "refresh")
            await uow.sessions_repo.add(
                id=sid,
                user_id=user.id,
                token_hash=token_hash(pair["refresh_token"]),
                expires_at=datetime.fromtimestamp(claims["exp"], UTC),
            )
            await uow.commit()
            return public(user), pair

    async def refresh(self, user_id, sid, raw):
        async with self.uow_factory() as uow:
            # User lock orders refresh against account deactivation.
            user = await uow.users.get(user_id, lock=True)
            session = await uow.sessions_repo.get(sid, lock=True)
            if (
                not user
                or not user.is_active
                or not session
                or session.user_id != user_id
                or session.revoked_at
                or session.expires_at <= datetime.now(UTC)
                or session.token_hash != token_hash(raw)
            ):
                raise AuthenticationError("Refresh session is no longer valid")
            pair = self.tokens.pair(user_id, sid)
            session.token_hash = token_hash(pair["refresh_token"])
            claims = self.tokens.verify(pair["refresh_token"], "refresh")
            session.expires_at = datetime.fromtimestamp(claims["exp"], UTC)
            await uow.commit()
            return pair

    async def logout(self, user_id, sid, raw):
        async with self.uow_factory() as uow:
            session = await uow.sessions_repo.get(sid, lock=True)
            if session and session.user_id == user_id and session.token_hash == token_hash(raw):
                session.revoked_at = datetime.now(UTC)
            await uow.commit()
