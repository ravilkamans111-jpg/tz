import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import PaymentStatus
from app.repositories import PaymentRepository
from app.services.gateway import PaymentGateway
from app.services.webhook import WebhookClient

logger = logging.getLogger(__name__)


class PaymentProcessor:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        gateway: PaymentGateway,
        webhook: WebhookClient,
    ):
        self.session_factory = session_factory
        self.gateway = gateway
        self.webhook = webhook

    async def process(self, payment_id: uuid.UUID) -> None:
        async with self.session_factory() as session:
            payment = await PaymentRepository(session).get(payment_id, for_update=True)
            if payment is None:
                logger.warning("Платеж %s не найден", payment_id)
                return

            if payment.status == PaymentStatus.PENDING:
                success = await self.gateway.charge()
                payment.status = PaymentStatus.SUCCEEDED if success else PaymentStatus.FAILED
                payment.processed_at = datetime.now(UTC)
                await session.commit()

            await self.webhook.send(payment)
