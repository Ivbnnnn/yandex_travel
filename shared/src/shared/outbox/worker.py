import asyncio
import logging

from shared.outbox.publisher import OutboxPublisher

logger = logging.getLogger(__name__)


async def run_outbox(
    publisher: OutboxPublisher,
    interval: float = 1.0,
) -> None:
    while True:
        try:
            count = await publisher.publish_batch()

            if count == 0:
                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Outbox publishing failed")

            await asyncio.sleep(interval)
