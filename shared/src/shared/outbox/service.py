from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models.outbox import OutboxEvent


def add_outbox_event(
    session: AsyncSession,
    *,
    topic: str,
    payload: BaseModel,
    key: str | None = None,
) -> OutboxEvent:
    event = OutboxEvent(
        topic=topic,
        key=key,
        payload=payload.model_dump(mode="json"),
    )

    session.add(event)

    return event