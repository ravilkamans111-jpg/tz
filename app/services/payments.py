from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import OutboxRepository, PaymentRepository
from app.models import Payment
from app.schemas import PaymentCreate

PAYMENT_CREATED = "payments.new"


class PaymentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.payments = PaymentRepository(session)
        self.outbox = OutboxRepository(session)

    async def create(self, data: PaymentCreate, idempotency_key: str) -> Payment:
        existing = await self.payments.get_by_key(idempotency_key)
        if existing:
            return existing

        payment = Payment(
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            meta=data.metadata,
            webhook_url=str(data.webhook_url),
            idempotency_key=idempotency_key,
        )
        self.payments.add(payment)
        await self.session.flush()
        self.outbox.add(PAYMENT_CREATED, {"payment_id": str(payment.id)})

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.payments.get_by_key(idempotency_key)
            if existing is None:
                raise
            return existing
        return payment

    async def get(self, payment_id) -> Payment | None:
        return await self.payments.get(payment_id)
