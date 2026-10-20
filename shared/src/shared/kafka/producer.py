from aiokafka import AIOKafkaProducer
from pydantic import BaseModel
from typing import ClassVar
import uuid
from aiokafka.structs import RecordMetadata

class BaseProducer:
    """Base class for kafka producer"""

    topic:ClassVar[str|None] = None

    def __init__(self, bootstrap_servers:str):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=self._serialize,
            key_serializer=lambda key: key.encode(),
            enable_idempotence=True
        )

    @classmethod
    def _serialize(value:BaseModel) -> bytes:
        return value.model_dump_json().encode()

    async def start(self) -> None:
        await self._producer.start()
    
    
    async def stop(self) -> None:
        await self._producer.stop()


    async def publish(
        self,
        event: BaseModel,
        topic: str | None = None,
        key: str | None = None,
        event_id: uuid.UUID | None = None,
    ) -> RecordMetadata:
        resolved_topic = (
            topic if topic is not None else self.topic
        )

        if resolved_topic is None:
            raise ValueError("Topic cannot be None")

        event_id = event_id or uuid.uuid4()

        return await self._producer.send_and_wait(
            topic=resolved_topic,
            value=event,
            key=key,
            headers=[
                ("event_id", str(event_id).encode()),
            ],
        )

