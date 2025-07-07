import json
from typing import Awaitable, Callable
from app.domain.events import CaseAssignedEvent, CaseSolutionsGeneratedEvent
from app.domain.protocols import EventPublisher
from aio_pika import ExchangeType, IncomingMessage, connect_robust, Message
from aio_pika.abc import AbstractRobustConnection

RABBIT_URL            = "amqp://guest:guest@localhost:5672/"
ASSIGNED_EXCHANGE = "Contracts.Shared.Events:CaseAssigned"
ASSIGNED_ROUTING_KEY  = "case-assigned"
ASSIGNED_QUEUE_NAME   = "ai-service.case-assigned"

async def start_case_assigned_consumer(
    callback: Callable[[CaseAssignedEvent], Awaitable[None]]
) -> AbstractRobustConnection:
    """
    Connect to RabbitMQ, bind to the 'case-assigned' exchange,
    and invoke `callback(evt)` for each incoming message.
    Returns the connection so the caller can close it on shutdown.
    """
    # 1) Establish a robust connection
    connection = await connect_robust(RABBIT_URL)
    channel    = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    # 2) Declare the exchange and queue, then bind them
    exchange = await channel.declare_exchange(
        name=ASSIGNED_EXCHANGE, 
        type=ExchangeType.FANOUT,
        durable=True
    )
    queue = await channel.declare_queue(
        name=ASSIGNED_QUEUE_NAME, durable=True
    )
    await queue.bind(exchange, routing_key=ASSIGNED_ROUTING_KEY)

    # 3) Message handler
    async def _on_message(message: IncomingMessage):
        async with message.process():
            raw = json.loads(message.body)
            payload = raw["message"]
            evt = CaseAssignedEvent.parse_obj(payload)


            # Delegate to your application handler
            await callback(evt)

    # 4) Start consuming
    await queue.consume(_on_message)
    return connection



class AioPikaEventPublisher(EventPublisher):
    def __init__(self, url: str, exchange_name: str, routing_key: str):
        self._url = url
        self._exchange_name = exchange_name
        self._routing_key = routing_key
        self._connection = None
    
    async def connect(self):
        """Establish and cache the RabbitMQ connection."""
        if self._connection is None or self._connection.is_closed:
            self._connection = await connect_robust(self._url)
    
    async def publish_solutions(self, evt:CaseSolutionsGeneratedEvent):

        await self.connect()

        channel = await self._connection.channel()
        exchange = await channel.declare_exchange(
            name=self._exchange_name,
            type=ExchangeType.FANOUT,
            durable=True
        )  

        message = Message(evt.json().encode())
        await exchange.publish(message,routing_key=self._routing_key)
    
    async def close(self):
        if self._connection and not self._connection.is_closed:
            await self._connection.close()