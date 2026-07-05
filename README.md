# AI Service

## Responsibility

The AI Service manages the generation side of the RAG pipeline for the AI-Aided Consultant Platform.

It is responsible for receiving a submitted case, retrieving relevant context from the Embedding Service, building a prompt using the case and retrieved context, calling a generation model, and returning structured AI-assisted draft recommendations.

The service supports consultants by preparing decision-support material. It does not make final decisions, does not send final advice to users, and does not replace the consultant. A human consultant remains responsible for reviewing, editing, validating, or replacing the generated draft before sending the final response to the user.

The AI Service does not store vectors, chunk PDFs, manage pgvector, or own knowledge persistence. Those responsibilities belong to the Embedding Service.

## Tech Stack

* FastAPI
* Python
* Pydantic
* HTTPX
* Hugging Face Inference Providers / OpenAI-compatible API
* RabbitMQ
* Swagger / OpenAPI
* Docker / Docker Compose

## Architecture

The AI Service follows Clean Architecture principles. The code is separated into the following layers:

* API: exposes HTTP endpoints through FastAPI routers.
* Application: contains use cases and event handlers for generating AI-assisted case drafts.
* Domain: contains models, events, and interfaces used by the application layer.
* Infrastructure: contains technical implementations such as HTTP clients, generation model adapters, prompt builders, response parsers, and RabbitMQ adapters.
* Core: contains cross-cutting configuration and shared exceptions.

The Application layer depends on abstractions such as `SimilaritySearchClient`, `GenerationModel`, `CaseServiceClient`, and `EventPublisher`.

The Infrastructure layer implements these abstractions using HTTP calls to the Embedding Service, OpenAI-compatible generation providers, HTTP calls to the Case Service, and RabbitMQ messaging.

Dependency creation is centralized in `app/main.py`, while API controllers remain focused on HTTP request and response handling.

## Main Endpoints

| Method | Endpoint                   | Description                                                                 |
| ------ | -------------------------- | --------------------------------------------------------------------------- |
| `POST` | `/v1/draft-recommendation` | Retrieves context and generates AI-assisted draft recommendations for a case. |
| `GET`  | `/health`                  | Returns the health status of the service.                                   |

## Main Components

* `app/main.py`: creates the FastAPI application and wires dependencies.
* `app/dependencies.py`: provides application use cases to API routes through FastAPI dependency injection.
* `api/v1/solve_case.py`: exposes the draft recommendation endpoint.
* `GenerateCaseDraftUseCase`: orchestrates retrieval, generation, and final response formatting.
* `CaseAssignedHandler`: handles case assignment events and triggers draft generation for assigned cases.
* `CaseQuery`: domain model representing the case query sent to the AI Service.
* `RetrievedContext`: domain model representing context returned by the Embedding Service.
* `DraftRecommendation`: domain model representing one AI-generated draft recommendation.
* `AIDraft`: domain model representing the structured AI draft shown to the consultant.
* `SolveCaseResult`: domain model representing the API response returned by the AI Service.
* `CaseAssignedEvent`: domain event consumed when a case is assigned to a consultant.
* `CaseDraftGeneratedEvent`: domain event published after draft generation.
* `SimilaritySearchClient`: abstraction for retrieving relevant context from the Embedding Service.
* `GenerationModel`: abstraction for calling a replaceable generation model.
* `CaseServiceClient`: abstraction for retrieving case data and sending generated drafts.
* `EventPublisher`: abstraction for publishing AI Service events.
* `EmbeddingServiceClient`: infrastructure implementation that calls the Embedding Service similarity search endpoint.
* `HttpxCaseServiceClient`: infrastructure implementation that communicates with the Case Service.
* `OpenAICompatibleGenerationModel`: infrastructure implementation for OpenAI-compatible chat completion APIs.
* `MockGenerationModel`: local development implementation that generates mock drafts without external model calls.
* `ConsultantPromptBuilder`: builds prompts using the case, speciality, language, prompt version, and retrieved context.
* `LLMResponseParser`: parses model output into the structured `AIDraft` domain model.
* `AioPikaEventPublisher`: RabbitMQ implementation for publishing AI Service events.
* `start_case_assigned_consumer`: RabbitMQ consumer for handling assigned-case events.

## Data Flow

### Draft Recommendation Flow

1. The client sends a `POST /v1/draft-recommendation` request.
2. The request contains the case text, retrieval settings, optional speciality, optional output language, and optional prompt version.
3. The controller reads the authenticated consultant/user ID from the `X-User-Id` header.
4. The controller calls `GenerateCaseDraftUseCase`.
5. `GenerateCaseDraftUseCase` calls `SimilaritySearchClient`.
6. `EmbeddingServiceClient` sends the query to the Embedding Service using `POST /embedding/similarity-search`.
7. The Embedding Service returns relevant text or PDF chunks.
8. `GenerateCaseDraftUseCase` calls `GenerationModel`.
9. `ConsultantPromptBuilder` builds the model messages using the case, retrieved context, speciality, language, and prompt version.
10. `OpenAICompatibleGenerationModel` calls the configured generation provider.
11. `LLMResponseParser` parses the model response into an `AIDraft`.
12. `GenerateCaseDraftUseCase` attaches retrieved context previews to the response.
13. The API returns the structured AI draft to the client.

### Mock Generation Flow

1. The environment variable `AI_PROVIDER` is set to `mock`.
2. The AI Service still retrieves context from the Embedding Service.
3. Instead of calling a real LLM provider, the service uses `MockGenerationModel`.
4. The mock model returns predictable draft recommendations.
5. This mode is useful for local development, testing, and demos without model API cost.

### Real Generation Flow

1. The environment variable `AI_PROVIDER` is set to `openai_compatible`.
2. The AI Service retrieves context from the Embedding Service.
3. The service builds a structured consultant-facing prompt.
4. `OpenAICompatibleGenerationModel` calls the configured OpenAI-compatible provider.
5. The model returns a JSON draft.
6. `LLMResponseParser` validates and converts the response into an `AIDraft`.
7. If parsing fails, the parser returns a safe fallback draft so the service does not crash.

### Case Assigned Event Flow

1. The Case Service publishes a case assignment event.
2. The AI Service consumes `CaseAssignedEvent` from RabbitMQ.
3. `CaseAssignedHandler` retrieves case details from the Case Service.
4. The handler creates a `CaseQuery` from the case description and metadata.
5. The handler calls `GenerateCaseDraftUseCase`.
6. The generated draft is sent back to the Case Service through `CaseServiceClient`.
7. Optionally, the AI Service publishes `CaseDraftGeneratedEvent`.

## RAG Pipeline Role

The AI Service represents the generation part of the RAG pipeline.

Its responsibilities are:

* receiving case queries
* requesting relevant context from the Embedding Service
* building prompts from case data and retrieved context
* calling a replaceable generation model
* parsing model output into structured drafts
* returning consultant-facing draft recommendations
* keeping the consultant responsible for final validation

The Embedding Service represents the retrieval and indexing part of the RAG pipeline.

Its responsibilities are:

* cleaning text
* chunking PDFs
* generating embeddings
* storing vectors
* querying Supabase/pgvector
* returning similar text and PDF chunks

A submitted user case is normally treated as a query. It should not automatically be stored as reusable experience. It should become reusable knowledge only after a consultant validates the final response.

## Communication With Other Services

| Service           | Communication Type         | Purpose                                                                                   |
| ----------------- | -------------------------- | ----------------------------------------------------------------------------------------- |
| API Gateway       | HTTP Request / HTTP Header | Routes external requests and provides authenticated user information through `X-User-Id`. |
| Embedding Service | HTTP Request               | Retrieves relevant context chunks for RAG-based generation.                              |
| Case Service      | HTTP Request               | Retrieves case details and stores generated AI drafts.                                   |
| Consultant Service| Event / Workflow           | Assigns cases to consultants and receives draft material for human review.                |
| RabbitMQ          | Asynchronous Messaging     | Consumes case assignment events and publishes draft-generated events.          |
| Hugging Face / LLM Provider | HTTP API          | Generates structured draft recommendations from prompts.                                 |

## Patterns Used

### Clean Architecture

The service separates code into API, Application, Domain, Infrastructure, and Core layers.

This keeps use cases independent from technical details such as FastAPI, HTTPX, Hugging Face, RabbitMQ, and external service URLs.

### Adapter Pattern

External systems are wrapped behind internal interfaces.

Examples:

* `EmbeddingServiceClient` adapts the Embedding Service API to the `SimilaritySearchClient` interface.
* `OpenAICompatibleGenerationModel` adapts hosted or local chat completion APIs to the `GenerationModel` interface.
* `MockGenerationModel` adapts local testing behavior to the `GenerationModel` interface.
* `HttpxCaseServiceClient` adapts the Case Service API to the `CaseServiceClient` interface.
* `AioPikaEventPublisher` adapts RabbitMQ publishing to the `EventPublisher` interface.

This makes it possible to replace external systems later without changing the Application layer.

### Dependency Injection

Dependencies are created during application startup in `app/main.py`.

The FastAPI app stores the main use case in `app.state`, and the API layer retrieves it through `app/dependencies.py`.

This avoids importing global service instances directly from `main.py`.

### Prompt Builder Pattern

Prompt construction is separated from the generation model.

`ConsultantPromptBuilder` builds messages from:

* case text
* retrieved context
* speciality
* language
* prompt version
* requested number of recommendations

This makes the service easier to extend later with prompt versioning, prompt evaluation, multilingual prompts, speciality-specific prompts, or agentic workflows.

### Provider Abstraction

The AI Service does not depend directly on one model provider.

Current provider options:

* `mock`: local development provider with no external LLM call.
* `openai_compatible`: provider for OpenAI-compatible chat completion APIs, including Hugging Face Inference Providers or local model servers.

This keeps hosted models replaceable and helps avoid vendor lock-in.


## Environment Variables

The AI Service uses environment variables to configure external dependencies, generation behavior, and messaging.

| Variable | Purpose |
| -------- | ------- |
| `ENV` | Runtime environment name used by the service. Example: `development`. |
| `APP_ENV` | Selects which `.env` file to load. Example: `development` loads `.env.development`. |
| `AI_PROVIDER` | Generation provider. Supported values: `mock`, `openai_compatible`. |
| `EMBEDDING_SERVICE_URL` | Base URL of the Embedding Service. |
| `CASE_SERVICE_URL` | Base URL of the Case Service. |
| `REQUEST_TIMEOUT` | Timeout in seconds for external HTTP requests. |
| `DEFAULT_SUGGESTION_COUNT` | Default number of draft recommendations to generate. |
| `LLM_API_BASE` | Base URL of the OpenAI-compatible model provider. |
| `LLM_MODEL_NAME` | Model name used by the generation provider. |
| `LLM_API_KEY` | API key or token used by the generation provider. |
| `LLM_TEMPERATURE` | Controls randomness of generated output. Lower values are more deterministic. |
| `LLM_MAX_TOKENS` | Maximum number of output tokens generated by the model. |
| `ENABLE_RABBITMQ_CONSUMER` | Enables or disables RabbitMQ case assignment consumption. |
| `RABBITMQ_URL` | RabbitMQ connection URL. |
| `CASE_ASSIGNED_EXCHANGE` | RabbitMQ exchange used for case assignment events. |
| `CASE_ASSIGNED_ROUTING_KEY` | Routing key used for case assignment events. |
| `CASE_ASSIGNED_QUEUE_NAME` | Queue consumed by the AI Service for case assignment events. |
| `CASE_DRAFT_GENERATED_EXCHANGE` | RabbitMQ exchange used for draft-generated events. |
| `CASE_DRAFT_GENERATED_ROUTING_KEY` | Routing key used for draft-generated events. |

Example local `.env.development` file:

```env
ENV=development
APP_ENV=development

AI_PROVIDER=mock

EMBEDDING_SERVICE_URL=http://127.0.0.1:5050
CASE_SERVICE_URL=http://127.0.0.1:5010

REQUEST_TIMEOUT=120
DEFAULT_SUGGESTION_COUNT=3

LLM_API_BASE=https://router.huggingface.co/v1
LLM_MODEL_NAME=Qwen/Qwen3-8B
LLM_API_KEY=
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1000

ENABLE_RABBITMQ_CONSUMER=false
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

CASE_ASSIGNED_EXCHANGE=Contracts.Shared.Events:CaseAssigned
CASE_ASSIGNED_ROUTING_KEY=case-assigned
CASE_ASSIGNED_QUEUE_NAME=ai-service.case-assigned

CASE_DRAFT_GENERATED_EXCHANGE=case-draft-generated
CASE_DRAFT_GENERATED_ROUTING_KEY=case.draft.generated
```

For local testing with a real Hugging Face model provider:

```env
AI_PROVIDER=openai_compatible
LLM_API_BASE=https://router.huggingface.co/v1
LLM_MODEL_NAME=Qwen/Qwen3-8B
LLM_API_KEY=your_huggingface_token
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1000
```

For Docker Compose, service URLs should use container service names instead of `127.0.0.1`:

```env
EMBEDDING_SERVICE_URL=http://embedding-service:8000
CASE_SERVICE_URL=http://case-service:8080
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

## Local Development

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env.development
```

Run the service locally:

```bash
uvicorn app.main:app --reload --port 8040
```

By default, the local manual development URL is:

```text
http://127.0.0.1:8040
```

Swagger documentation is available at:

```text
http://127.0.0.1:8040/docs
```

Health check:

```text
http://127.0.0.1:8040/health
```

The Embedding Service must be running before testing draft generation because the AI Service calls it for similarity search.

Example Embedding Service local URL:

```text
http://127.0.0.1:5050
```

## Docker

Build the Docker image:

```bash
docker build -t ai-service .
```

Run the container:

```bash
docker run --env-file .env.development -p 8040:8000 ai-service
```

The container exposes the service internally on port `8000`.

When running with Docker Compose, environment variables should usually be provided by the compose file or deployment platform rather than copied into the image.

## Example Requests

### Generate Draft Recommendation

```http
POST /v1/draft-recommendation?n=3
X-User-Id: 11111111-1111-1111-1111-111111111111
Content-Type: application/json
```

```json
{
  "case_id": null,
  "text": "The user is asking whether they should use a monolithic architecture or microservices for a small final-year project.",
  "k": 5,
  "min_similarity": 0.7,
  "speciality": "software architecture",
  "language": "en",
  "prompt_version": "default_v1"
}
```

Example response:

```json
{
  "case_id": null,
  "draft": {
    "summary": "A student is deciding between monolithic and microservices architecture for a small final-year project.",
    "recommendations": [
      {
        "title": "Consider Monolithic Architecture",
        "content": "For a small project with limited complexity, a monolithic architecture may be more straightforward to implement and manage.",
        "reasoning": "The retrieved context indicates that monolithic architectures are easier to develop, test, deploy, and maintain for smaller projects."
      },
      {
        "title": "Evaluate Project Requirements",
        "content": "Assess whether the project's scope, team size, and future scalability needs justify the complexity of microservices.",
        "reasoning": "The context suggests microservices are better suited for larger teams or projects requiring independent scaling and bounded contexts."
      },
      {
        "title": "Prioritize Simplicity and Learning Goals",
        "content": "Choose the architecture that aligns with the project's learning objectives and the student's familiarity with the technology.",
        "reasoning": "The context emphasizes that simplicity and maintainability are critical factors for small projects."
      }
    ],
    "missing_information": [
      "The specific complexity of the project's requirements.",
      "The student's familiarity with different architectural patterns.",
      "Whether the project will evolve into a larger system in the future."
    ],
    "important_notes": [
      "Microservices introduce additional complexity that may not be justified for small projects.",
      "This is an AI-generated draft and must be reviewed by a human consultant before being sent to the user."
    ],
    "used_context": [
      {
        "id": "fb706ab1-6be3-49c0-98c7-1de2fa7ee422",
        "source": "text",
        "pdf_id": null,
        "similarity": 0.79096794128418,
        "text_preview": "For small final-year projects, a monolithic architecture is often easier to develop, test, deploy, and maintain. Microservices are useful when teams are large, services need independent scaling, or the domain is clearly divided into independent bounded contexts."
      }
    ]
  }
}
```

