from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OutboxEvent


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, event_type: str, payload: dict) -> None:
        self.session.add(OutboxEvent(event_type=event_type, payload=payload))

    async def fetch_unpublished(self, limit: int) -> list[OutboxEvent]:
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(await self.session.scalars(query))
