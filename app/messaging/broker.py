from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue

PAYMENTS_EXCHANGE_NAME = "payments"
PAYMENTS_DLX_NAME = "payments.dlx"
PAYMENTS_RETRY_EXCHANGE_NAME = "payments.retry"

payments_exchange = RabbitExchange(PAYMENTS_EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True)
payments_dlx = RabbitExchange(PAYMENTS_DLX_NAME, type=ExchangeType.DIRECT, durable=True)
payments_retry_exchange = RabbitExchange(
    PAYMENTS_RETRY_EXCHANGE_NAME, type=ExchangeType.DIRECT, durable=True
)

payments_new_queue = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key="payments.new",
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX_NAME,
        "x-dead-letter-routing-key": "payments.dlq",
    },
)

payments_retry_queue = RabbitQueue(
    "payments.retry",
    durable=True,
    routing_key="payments.retry",
    arguments={
        "x-dead-letter-exchange": PAYMENTS_EXCHANGE_NAME,
        "x-dead-letter-routing-key": "payments.new",
    },
)

payments_dlq = RabbitQueue(
    "payments.dlq",
    durable=True,
    routing_key="payments.dlq",
)
