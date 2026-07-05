import json
import logging
import os
from typing import Awaitable, Callable

from aio_pika import ExchangeType, IncomingMessage, Message, connect_robust
from aio_pika.abc import AbstractRobustConnection

from app.domain.events import CaseAssignedEvent, CaseDraftGeneratedEvent
from app.domain.protocols import EventPublisher

logger = logging.getLogger(__name__)


RABBIT_URL = os.getenv(
    "RABBITMQ_URL",
    "amqp://guest:guest@localhost:5672/",
)

CASE_ASSIGNED_EXCHANGE = os.getenv(
    "CASE_ASSIGNED_EXCHANGE",
    "Contracts.Shared.Events:CaseAssigned",
)

CASE_ASSIGNED_ROUTING_KEY = os.getenv(
    "CASE_ASSIGNED_ROUTING_KEY",
    "case-assigned",
)

CASE_ASSIGNED_QUEUE_NAME = os.getenv(
    "CASE_ASSIGNED_QUEUE_NAME",
    "ai-service.case-assigned",
)

CASE_DRAFT_GENERATED_EXCHANGE = os.getenv(
    "CASE_DRAFT_GENERATED_EXCHANGE",
    "case-draft-generated",
)

CASE_DRAFT_GENERATED_ROUTING_KEY = os.getenv(
    "CASE_DRAFT_GENERATED_ROUTING_KEY",
    "case.draft.generated",
)


async def start_case_assigned_consumer(
    callback: Callable[[CaseAssignedEvent], Awaitable[None]],
    url: str = RABBIT_URL,
    exchange_name: str = CASE_ASSIGNED_EXCHANGE,
    routing_key: str = CASE_ASSIGNED_ROUTING_KEY,
    queue_name: str = CASE_ASSIGNED_QUEUE_NAME,
) -> AbstractRobustConnection:
    """
    Start consuming CaseAssignedEvent messages.

    The expected incoming format is compatible with MassTransit-style envelopes:
    {
      "message": {
        "caseId": "...",
        "consultantId": "..."
      }
    }
    """

    connection = await connect_robust(url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        name=exchange_name,
        type=ExchangeType.FANOUT,
        durable=True,
    )

    queue = await channel.declare_queue(
        name=queue_name,
        durable=True,
    )

    await queue.bind(exchange, routing_key=routing_key)

    async def on_message(message: IncomingMessage) -> None:
        async with message.process():
            raw = json.loads(message.body)

            payload = raw.get("message", raw)

            event = CaseAssignedEvent.model_validate(payload)

            logger.info(
                "Received CaseAssignedEvent case_id=%s consultant_id=%s",
                event.case_id,
                event.consultant_id,
            )

            await callback(event)

    await queue.consume(on_message)

    logger.info("Started CaseAssignedEvent consumer")

    return connection


class AioPikaEventPublisher(EventPublisher):
    """
    RabbitMQ publisher for AI Service events.
    """

    def __init__(
        self,
        url: str = RABBIT_URL,
        exchange_name: str = CASE_DRAFT_GENERATED_EXCHANGE,
        routing_key: str = CASE_DRAFT_GENERATED_ROUTING_KEY,
    ) -> None:
        self._url = url
        self._exchange_name = exchange_name
        self._routing_key = routing_key
        self._connection: AbstractRobustConnection | None = None

    async def connect(self) -> None:
        if self._connection is None or self._connection.is_closed:
            self._connection = await connect_robust(self._url)

    async def publish_case_draft_generated(
        self,
        event: CaseDraftGeneratedEvent,
    ) -> None:
        await self.connect()

        assert self._connection is not None

        channel = await self._connection.channel()

        exchange = await channel.declare_exchange(
            name=self._exchange_name,
            type=ExchangeType.FANOUT,
            durable=True,
        )

        payload = event.model_dump_json(by_alias=True).encode("utf-8")

        message = Message(
            body=payload,
            content_type="application/json",
        )

        await exchange.publish(
            message,
            routing_key=self._routing_key,
        )

        logger.info(
            "Published CaseDraftGeneratedEvent case_id=%s consultant_id=%s",
            event.case_id,
            event.consultant_id,
        )

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()