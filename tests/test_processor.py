import pytest

from app.models import Currency, Payment, PaymentStatus
from app.services.processor import PaymentProcessor


class FakeGateway:
    def __init__(self, success: bool):
        self.success = success
        self.calls = 0

    async def charge(self) -> bool:
        self.calls += 1
        return self.success


class FakeWebhook:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.sent: list[Payment] = []

    async def send(self, payment: Payment) -> None:
        if self.fail:
            raise RuntimeError("webhook недоступен")
        self.sent.append(payment)


@pytest.fixture
async def payment(session_factory):
    async with session_factory() as session:
        payment = Payment(
            amount=10,
            currency=Currency.USD,
            description="test",
            meta={},
            idempotency_key="k",
            webhook_url="https://example.com/hook",
        )
        session.add(payment)
        await session.commit()
        return payment


async def reload(session_factory, payment_id):
    async with session_factory() as session:
        return await session.get(Payment, payment_id)


@pytest.mark.parametrize(
    ("success", "expected"),
    [(True, PaymentStatus.SUCCEEDED), (False, PaymentStatus.FAILED)],
)
async def test_process_sets_status_and_sends_webhook(session_factory, payment, success, expected):
    webhook = FakeWebhook()
    processor = PaymentProcessor(session_factory, FakeGateway(success), webhook)

    await processor.process(payment.id)

    saved = await reload(session_factory, payment.id)
    assert saved.status == expected
    assert saved.processed_at is not None
    assert len(webhook.sent) == 1
    assert webhook.sent[0].status == expected


async def test_repeated_delivery_does_not_charge_twice(session_factory, payment):
    gateway = FakeGateway(True)
    webhook = FakeWebhook()
    processor = PaymentProcessor(session_factory, gateway, webhook)

    await processor.process(payment.id)
    await processor.process(payment.id)

    assert gateway.calls == 1
    assert len(webhook.sent) == 2


async def test_webhook_error_keeps_payment_status(session_factory, payment):
    processor = PaymentProcessor(session_factory, FakeGateway(True), FakeWebhook(fail=True))

    with pytest.raises(RuntimeError):
        await processor.process(payment.id)

    saved = await reload(session_factory, payment.id)
    assert saved.status == PaymentStatus.SUCCEEDED


async def test_unknown_payment_is_ignored(session_factory):
    import uuid

    gateway = FakeGateway(True)
    processor = PaymentProcessor(session_factory, gateway, FakeWebhook())

    await processor.process(uuid.uuid4())

    assert gateway.calls == 0
