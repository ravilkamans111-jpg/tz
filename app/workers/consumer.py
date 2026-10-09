import asyncio
import logging

from faststream import AckPolicy, FastStream

from app.broker import (
    broker,
    dead_letter_exchange,
    dead_letter_queue,
    payments_exchange,
    payments_queue,
)
from app.config import settings
from app.db import session_factory
from app.schemas import PaymentEvent
from app.services.gateway import PaymentGateway
from app.services.processor import PaymentProcessor
from app.services.retry import with_retry
from app.services.webhook import WebhookClient
from app.workers.outbox import OutboxPublisher

logging.basicConfig(level=logging.INFO)

processor = PaymentProcessor(session_factory, PaymentGateway(), WebhookClient())
outbox_publisher = OutboxPublisher(session_factory, broker)
_background: set[asyncio.Task] = set()


@broker.subscriber(payments_queue, payments_exchange, ack_policy=AckPolicy.REJECT_ON_ERROR)
async def handle_new_payment(event: PaymentEvent) -> None:
    await with_retry(
        lambda: processor.process(event.payment_id),
        attempts=settings.max_attempts,
        base_delay=settings.retry_base_delay,
    )


async def declare_dead_letter_queue() -> None:
    exchange = await broker.declare_exchange(dead_letter_exchange)
    queue = await broker.declare_queue(dead_letter_queue)
    await queue.bind(exchange, routing_key=dead_letter_queue.routing_key)


async def start_outbox() -> None:
    task = asyncio.create_task(outbox_publisher.run())
    _background.add(task)
    task.add_done_callback(_background.discard)


async def stop_outbox() -> None:
    for task in list(_background):
        task.cancel()


app = FastStream(
    broker,
    after_startup=[declare_dead_letter_queue, start_outbox],
    on_shutdown=[stop_outbox],
)
