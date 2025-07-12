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


embedding_client = EmbeddingClient()
llm_client = LLMClient()

retrieval  = EmbeddingRetrieval(embedding_client)
generation = APIGenerator(api_key=settings.LLM_API_KEY,model_name="deepseek-r1-distill-llama-70b",stream=False)

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

    # 1) Publisher for solutions
    publisher = AioPikaEventPublisher(
        url="amqp://guest:guest@localhost:5672/",
        exchange_name="case-solutions-generated",
        routing_key="case.solutions.generated"
    )
    await publisher.connect()

    # 2) HTTP client for CaseService
    case_client = HttpxCaseServiceClient(base_url="http://localhost:5010/")

    # 3) Your RAG logic
    rag: RagService = get_rag_service()

    # 4) Compose the handler
    handler = CaseAssignedHandler(
        case_client=case_client,
        publisher=publisher,
        rag=rag
    )

    # 5) Start the consumer, passing in handler.handle
    rabbit_connection = await start_case_assigned_consumer(handler.handle)
    # app.logger.info("✅ RabbitMQ consumer for CaseAssigned started")

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
