from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from app.config import settings

PAYMENTS_ROUTING_KEY = "payments.new"
DLQ_ROUTING_KEY = "payments.dlq"

broker = RabbitBroker(settings.rabbitmq_url)

payments_exchange = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
dead_letter_exchange = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)

payments_queue = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key=PAYMENTS_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": dead_letter_exchange.name,
        "x-dead-letter-routing-key": DLQ_ROUTING_KEY,
    },
)
dead_letter_queue = RabbitQueue("payments.dlq", durable=True, routing_key=DLQ_ROUTING_KEY)
