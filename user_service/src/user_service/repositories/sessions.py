import hashlib
from datetime import UTC, datetime
from uuid import UUID

from shared.db.repository import BaseRepository
from sqlalchemy import select, update

from ..db import RefreshSession
from ..schemas import RefreshSessionCreateRepo, RefreshSessionRevoke


class SessionRepository(
    BaseRepository[RefreshSession, RefreshSessionCreateRepo, RefreshSessionRevoke]
):
    model = RefreshSession

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def insert(self, data: RefreshSessionCreateRepo) -> RefreshSession:
        session = RefreshSession(
            id=data.id,
            user_id=data.user_id,
            token_hash=self._hash_token(data.token),
            expires_at=data.expires_at,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def read(self, id: UUID) -> RefreshSession | None:
        return await self.session.get(RefreshSession, id)

    async def get_active(self, session_id: UUID, token: str) -> RefreshSession | None:
        stmt = select(RefreshSession).where(
            RefreshSession.id == session_id,
            RefreshSession.token_hash == self._hash_token(token),
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(UTC),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def rotate(
        self,
        session_id: UUID,
        old_token: str,
        new_token: str,
        expires_at: datetime,
    ) -> RefreshSession | None:
        if old_token == new_token:
            raise ValueError("New refresh token must differ from the old one")

        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.id == session_id,
                RefreshSession.token_hash == self._hash_token(old_token),
                RefreshSession.revoked_at.is_(None),
                RefreshSession.expires_at > datetime.now(UTC),
            )
            .values(
                token_hash=self._hash_token(new_token),
                expires_at=expires_at,
            )
            .returning(RefreshSession)
            .execution_options(synchronize_session="fetch")
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, session_id: UUID, token: str) -> RefreshSession | None:
        stmt = (
            update(RefreshSession)
            .where(
                RefreshSession.id == session_id,
                RefreshSession.token_hash == self._hash_token(token),
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
            .returning(RefreshSession)
            .execution_options(synchronize_session="fetch")
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
