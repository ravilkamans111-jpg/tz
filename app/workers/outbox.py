import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.broker import PAYMENTS_ROUTING_KEY, payments_exchange
from app.config import settings
from app.repositories import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxPublisher:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], broker):
        self.session_factory = session_factory
        self.broker = broker

    async def publish_pending(self) -> int:
        async with self.session_factory() as session:
            events = await OutboxRepository(session).fetch_unpublished(settings.outbox_batch_size)
            for event in events:
                await self.broker.publish(
                    event.payload,
                    exchange=payments_exchange,
                    routing_key=PAYMENTS_ROUTING_KEY,
                    persist=True,
                )
                event.published_at = datetime.now(UTC)
            await session.commit()
            return len(events)

    async def run(self) -> None:
        while True:
            try:
                published = await self.publish_pending()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Ошибка публикации событий outbox")
                published = 0
            if not published:
                await asyncio.sleep(settings.outbox_poll_interval)
