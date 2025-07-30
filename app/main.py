import asyncio
import logging
from aiormq import AMQPConnectionError
from fastapi import Depends, FastAPI
from app.clients.embedding_client import EmbeddingClient
from app.core.config import get_settings
from app.infrastructure.httpx_client import HttpxCaseServiceClient
from app.infrastructure.rabbitmq_adapter import AioPikaEventPublisher, start_case_assigned_consumer
from app.services.case_assigned_handler import CaseAssignedHandler
from app.services.retrieval import EmbeddingRetrieval
from app.clients.llm_client import LLMClient
from app.services.generation import APIGenerator, LlamaGeneration
from app.services.rag_service import RagService
from app.api.v1.solve_case import router as solve_router

settings = get_settings()


logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

embedding_client = EmbeddingClient()
llm_client = LLMClient()

retrieval  = EmbeddingRetrieval(embedding_client)
generation = APIGenerator(api_key=settings.LLM_API_KEY,model_name="llama-3.3-70b-versatile",stream=False)

rag_service = RagService(
    retrieval=retrieval,
    generation=generation,
    pre_processors=[],
)

app = FastAPI(
    title="RAG Case-Solver",
    version="0.1.0",
    description="Retrieve relevant documents and generate solution suggestions via RAG",
)

def get_rag_service() -> RagService:
    return rag_service

@app.on_event("startup")
async def on_startup():
    embedding_client = EmbeddingClient()
    llm_client = LLMClient()

    retrieval  = EmbeddingRetrieval(embedding_client)
    generation = LlamaGeneration(llm_client)

    global rabbit_connection, publisher

    publisher = AioPikaEventPublisher(
        url="amqp://guest:guest@rabbitmq:5672/",
        exchange_name="case-solutions-generated",
        routing_key="case.solutions.generated"
    )
    
    logger = logging.getLogger(__name__)

    for attempt in range(1, 7):
        try:
            await publisher.connect()
            logger.info("✅ Connected to RabbitMQ on attempt %d", attempt)
            break
        except AMQPConnectionError as e:
            logger.warning(
                "RabbitMQ not ready (attempt %d): %s; retrying in 5s…",
                attempt, e
            )
            await asyncio.sleep(5)
    else:
        logger.error("Could not connect to RabbitMQ after multiple attempts")
        raise RuntimeError("RabbitMQ connection failed")

    case_client = HttpxCaseServiceClient(base_url="http://cases:8080/")

    rag: RagService = get_rag_service()

    handler = CaseAssignedHandler(
        case_client=case_client,
        publisher=publisher,
        rag=rag
    )

    rabbit_connection = await start_case_assigned_consumer(handler.handle)

    s = get_settings()
    print("Settings",s.ENV)
    


app.include_router(
    solve_router,
    prefix="/v1",
    dependencies=[],
    tags=["solve-case"],
)

@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok"}
