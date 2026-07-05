import asyncio
import logging
from contextlib import asynccontextmanager

from aiormq import AMQPConnectionError
from fastapi import FastAPI

from app.api.v1.solve_case import router as solve_case_router
from app.application.handlers.case_assigned_handler import CaseAssignedHandler
from app.application.use_cases.generate_case_draft import GenerateCaseDraftUseCase
from app.core.config import get_settings
from app.infrastructure.clients.case_service_client import HttpxCaseServiceClient
from app.infrastructure.clients.embedding_service_client import EmbeddingServiceClient
from app.infrastructure.generation.mock_generation_model import MockGenerationModel
from app.infrastructure.generation.openai_compatible_generation_model import (
    OpenAICompatibleGenerationModel,
)
from app.infrastructure.rabbitmq_adapter import (
    AioPikaEventPublisher,
    start_case_assigned_consumer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def build_generation_model(settings):
    provider = settings.AI_PROVIDER.lower()

    if provider == "mock":
        logger.info("Using MockGenerationModel")
        return MockGenerationModel()

    if provider == "openai_compatible":
        logger.info(
            "Using OpenAI-compatible generation model: %s",
            settings.LLM_MODEL_NAME,
        )

        return OpenAICompatibleGenerationModel(
            base_url=settings.LLM_API_BASE,
            model_name=settings.LLM_MODEL_NAME,
            api_key=settings.LLM_API_KEY,
            timeout=settings.REQUEST_TIMEOUT,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

    raise ValueError(f"Unsupported AI_PROVIDER: {settings.AI_PROVIDER}")


async def connect_rabbitmq_with_retries(publisher, attempts: int = 6) -> None:
    for attempt in range(1, attempts + 1):
        try:
            await publisher.connect()
            logger.info("Connected to RabbitMQ on attempt %s", attempt)
            return

        except AMQPConnectionError as exc:
            logger.warning(
                "RabbitMQ not ready on attempt %s/%s: %s",
                attempt,
                attempts,
                exc,
            )
            await asyncio.sleep(5)

    raise RuntimeError("RabbitMQ connection failed after multiple attempts")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    similarity_search_client = EmbeddingServiceClient(
        base_url=settings.EMBEDDING_SERVICE_URL,
        timeout=settings.REQUEST_TIMEOUT,
        token=settings.EMBEDDING_SERVICE_TOKEN,
    )

    generation_model = build_generation_model(settings)

    generate_case_draft_use_case = GenerateCaseDraftUseCase(
        similarity_search_client=similarity_search_client,
        generation_model=generation_model,
        default_suggestion_count=settings.DEFAULT_SUGGESTION_COUNT,
    )

    app.state.generate_case_draft_use_case = generate_case_draft_use_case
    app.state.rabbit_connection = None
    app.state.rabbit_publisher = None

    if settings.ENABLE_RABBITMQ_CONSUMER:
        publisher = AioPikaEventPublisher(
            url=settings.RABBITMQ_URL,
            exchange_name=settings.CASE_DRAFT_GENERATED_EXCHANGE,
            routing_key=settings.CASE_DRAFT_GENERATED_ROUTING_KEY,
        )

        await connect_rabbitmq_with_retries(publisher)

        case_client = HttpxCaseServiceClient(
            base_url=settings.CASE_SERVICE_URL,
            timeout=30,
        )

        handler = CaseAssignedHandler(
            case_client=case_client,
            generate_case_draft_use_case=generate_case_draft_use_case,
            publisher=publisher,
        )

        rabbit_connection = await start_case_assigned_consumer(
            callback=handler.handle,
            url=settings.RABBITMQ_URL,
            exchange_name=settings.CASE_ASSIGNED_EXCHANGE,
            routing_key=settings.CASE_ASSIGNED_ROUTING_KEY,
            queue_name=settings.CASE_ASSIGNED_QUEUE_NAME,
        )

        app.state.rabbit_connection = rabbit_connection
        app.state.rabbit_publisher = publisher

        logger.info("RabbitMQ consumer enabled")

    else:
        logger.info("RabbitMQ consumer disabled")

    logger.info("AI Service started in ENV=%s", settings.ENV)

    yield

    rabbit_connection = getattr(app.state, "rabbit_connection", None)

    if rabbit_connection and not rabbit_connection.is_closed:
        await rabbit_connection.close()
        logger.info("RabbitMQ consumer connection closed")

    publisher = getattr(app.state, "rabbit_publisher", None)

    if publisher:
        await publisher.close()
        logger.info("RabbitMQ publisher connection closed")


app = FastAPI(
    title="AI Service",
    version="0.2.0",
    description=(
        "Generation side of the AI-Aided Consultant Platform. "
        "Retrieves context from the Embedding Service and generates "
        "AI-assisted draft recommendations for human consultant review."
    ),
    lifespan=lifespan,
)


app.include_router(
    solve_case_router,
    prefix="/v1",
    tags=["AI Draft Generation"],
)


@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok"}