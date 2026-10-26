import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from shared.db.models.outbox import OutboxEvent
from shared.kafka.producer import BaseProducer

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        producer: BaseProducer,
        batch_size: int = 100,
    ):
        self.session_factory = session_factory
        self.producer = producer
        self.batch_size = batch_size

    async def publish_batch(self) -> int:
        async with self.session_factory() as session:
            async with session.begin():
                stmt = (
                    select(OutboxEvent)
                    .where(OutboxEvent.published_at.is_(None))
                    .order_by(OutboxEvent.created_at)
                    .limit(self.batch_size)
                    .with_for_update(skip_locked=True)
                )

                result = await session.scalars(stmt)
                events = result.all()

                for event in events:
                    await self.producer.publish(
                        topic=event.topic,
                        key=event.key,
                        value=event.payload,
                    )

                    event.published_at = datetime.now(timezone.utc)

                return len(events)
