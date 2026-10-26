import logging
import uuid
from typing import ClassVar

from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel
from shared.db.models.inbox import InboxEvent
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

logger = logging.getLogger(__name__)


class BaseConsumer:
    topic: ClassVar[str | None] = None
    group_id: ClassVar[str | None] = None
    event_schema: ClassVar[type[BaseModel]] = BaseModel

    def __init__(
        self,
        bootstrap_servers: str,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._bootstrap_servers = bootstrap_servers
        self._session_factory = session_factory
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self, topic: str | None = None) -> None:
        resolved_topic = topic if topic is not None else self.topic

        if resolved_topic is None:
            raise ValueError("Kafka topic is not specified")

        if self.group_id is None:
            raise ValueError("Kafka group_id is not specified")

        self._consumer = AIOKafkaConsumer(
            resolved_topic,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,
            value_deserializer=(self.event_schema.model_validate_json),
        )

        await self._consumer.start()

    async def consume(self) -> None:
        if self._consumer is None:
            raise RuntimeError("Consumer is not started")

        async for message in self._consumer:
            headers = dict(message.headers)

            raw_event_id = headers.get("event_id")

            if raw_event_id is None:
                raise ValueError("Event ID is missing")

            event_id = uuid.UUID(raw_event_id.decode())

            async with self._session_factory() as session:
                async with session.begin():
                    stmt = (
                        insert(InboxEvent)
                        .values(
                            event_id=event_id,
                            group_id=self.group_id,
                        )
                        .on_conflict_do_nothing()
                        .returning(InboxEvent.event_id)
                    )

                    result = await session.scalar(stmt)

                    if result is not None:
                        await self.handle(
                            session,
                            message.value,
                        )
                    else:
                        logger.info(
                            "Duplicate event skipped: %s",
                            event_id,
                        )

            # Только после COMMIT в PostgreSQL
            await self._consumer.commit()

    async def handle(
        self,
        session: AsyncSession,
        event: BaseModel,
    ) -> None:
        raise NotImplementedError("Implement handle() in subclass")

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
