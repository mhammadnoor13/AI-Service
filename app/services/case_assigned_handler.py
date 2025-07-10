from app.domain.events import CaseAssignedEvent, CaseSolutionsGeneratedEvent, CaseSuggestions
from app.domain.models import CaseQuery, Suggestion
from app.domain.protocols import CaseServiceClient, EventPublisher
from app.services.rag_service import RagService


class CaseAssignedHandler:
    def __init__(
        self,
        case_client:CaseServiceClient,
        publisher: EventPublisher,
        rag: RagService
    ):
        self._case_client = case_client
        self._publisher = publisher
        self._rag = rag
    
    async def handle (self, evt: CaseAssignedEvent)->None:
        case_data = await self._case_client.get_case(evt.caseId)
        
        case_query = CaseQuery(text=case_data["description"],k=10)
        res = await self._rag.solve_case(case_query)
        out_msg = CaseSuggestions(
            case_id = evt.caseId,
            suggestions= res.suggestions
        )

        await self._case_client.post_case(out_msg)