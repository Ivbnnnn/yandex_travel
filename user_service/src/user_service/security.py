from dataclasses import dataclass
from uuid import UUID

from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool


@dataclass(frozen=True)
class RefreshCredentials:
    token: str
    user_id: int
    session_id: UUID


class PasswordService:
    def __init__(self):
        self.hasher = PasswordHash.recommended()
        self.dummy_hash = self.hasher.hash("dummy-password-for-login-timing")

    async def hash(self, password: str) -> str:
        return await run_in_threadpool(self.hasher.hash, password)

    async def verify(self, password: str, password_hash: str | None) -> bool:
        valid = await run_in_threadpool(
            self.hasher.verify, password, password_hash or self.dummy_hash
        )
        return valid and password_hash is not None
