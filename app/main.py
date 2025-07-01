# main.py

from fastapi import FastAPI
from app.clients.embedding_client import EmbeddingClient
from app.core.config import get_settings
from app.services.retrieval import EmbeddingRetrieval
from app.clients.llm_client import LLMClient
from app.services.generation import LlamaGeneration
from app.services.rag_service import RagService
from app.api.v1.solve_case import router as solve_router

# 1. Load settings
settings = get_settings()

# 2. Instantiate HTTP clients
embedding_client = EmbeddingClient()
llm_client       = LLMClient()

# 3. Build strategies
retrieval  = EmbeddingRetrieval(embedding_client)
generation = LlamaGeneration(llm_client)

# 4. Create the RagService (no pre-processors for now)
rag_service = RagService(
    retrieval=retrieval,
    generation=generation,
    pre_processors=[],
)

# 5. Create FastAPI app and include router
app = FastAPI(
    title="RAG Case-Solver",
    version="0.1.0",
    description="Retrieve relevant documents and generate solution suggestions via RAG",
)

# Make rag_service available to routers via dependency
def get_rag_service() -> RagService:
    return rag_service

app.include_router(
    solve_router,
    prefix="/v1",
    dependencies=[],
    tags=["solve-case"],
)

# 6. (Optional) health check
@app.get("/health", summary="Health check")
async def health():
    return {"status": "ok"}
