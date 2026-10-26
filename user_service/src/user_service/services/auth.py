from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from shared.auth import AuthenticateService

from ..db import User
from ..exceptions import InvalidCredentialsError, InvalidRefreshTokenError
from ..repositories import SessionRepository, UserRepository
from ..schemas import RefreshSessionCreateRepo, UserLogin
from ..security import PasswordService, RefreshCredentials


@dataclass(frozen=True)
class LoginResult:
    user: User
    tokens: dict[str, str]


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        tokens: AuthenticateService,
        passwords: PasswordService,
    ):
        self.users = users
        self.sessions = sessions
        self.session = users.session
        self.tokens = tokens
        self.passwords = passwords

    def _expires_at(self, refresh_token: str) -> datetime:
        claims = self.tokens.verify_refresh_token(refresh_token)
        return datetime.fromtimestamp(claims["exp"], UTC)

    async def login(self, data: UserLogin) -> LoginResult:
        async with self.session.begin():
            user = await self.users.get_user_by_email(str(data.email))
            password_hash = user.password_hash if user else None
            if not await self.passwords.verify(data.password, password_hash):
                raise InvalidCredentialsError()
            session_id = uuid4()
            tokens = self.tokens.create_token_pair(str(user.id), str(session_id))
            await self.sessions.insert(
                RefreshSessionCreateRepo(
                    id=session_id,
                    user_id=user.id,
                    token=tokens["refresh_token"],
                    expires_at=self._expires_at(tokens["refresh_token"]),
                )
            )
            return LoginResult(user=user, tokens=tokens)

    async def refresh(self, credentials: RefreshCredentials) -> dict[str, str]:
        async with self.session.begin():
            session = await self.sessions.get_active(credentials.session_id, credentials.token)
            if session is None or session.user_id != credentials.user_id:
                raise InvalidRefreshTokenError()
            if await self.users.read(credentials.user_id) is None:
                raise InvalidRefreshTokenError()
            tokens = self.tokens.create_token_pair(
                str(credentials.user_id), str(credentials.session_id)
            )
            rotated = await self.sessions.rotate(
                credentials.session_id,
                credentials.token,
                tokens["refresh_token"],
                self._expires_at(tokens["refresh_token"]),
            )
            if rotated is None:
                raise InvalidRefreshTokenError()
            return tokens

    async def logout(self, credentials: RefreshCredentials) -> None:
        async with self.session.begin():
            # A repeated logout for the same token is safe and returns success.
            await self.sessions.revoke(credentials.session_id, credentials.token)
