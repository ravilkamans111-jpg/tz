from app.models import OutboxEvent
from app.workers.outbox import OutboxPublisher


class FakeBroker:
    def __init__(self):
        self.messages = []

    async def publish(self, payload, **kwargs):
        self.messages.append((payload, kwargs["routing_key"]))


async def add_events(session_factory, n):
    async with session_factory() as session:
        for i in range(n):
            session.add(OutboxEvent(event_type="payments.new", payload={"payment_id": str(i)}))
        await session.commit()


async def test_publishes_pending_events_once(session_factory):
    await add_events(session_factory, 2)
    broker = FakeBroker()
    publisher = OutboxPublisher(session_factory, broker)

    assert await publisher.publish_pending() == 2
    assert await publisher.publish_pending() == 0

    assert [m[0] for m in broker.messages] == [{"payment_id": "0"}, {"payment_id": "1"}]
    assert broker.messages[0][1] == "payments.new"


async def test_event_stays_unpublished_when_broker_fails(session_factory):
    await add_events(session_factory, 1)

    class BrokenBroker:
        async def publish(self, *args, **kwargs):
            raise ConnectionError

    publisher = OutboxPublisher(session_factory, BrokenBroker())
    try:
        await publisher.publish_pending()
    except ConnectionError:
        pass

    working = FakeBroker()
    assert await OutboxPublisher(session_factory, working).publish_pending() == 1
