from typing import List, Optional
from pydantic import BaseModel, Field


class CaseQuery(BaseModel):
    text: str = Field(..., description="The raw user query or case description")
    k: int = Field(..., ge=1, description="Number of similar documents to retrieve") 
    consultant_id: Optional[str] = None # TODO Add them in the query
    speciality: Optional[str] = None

class Document(BaseModel):
    id:str
    snippet:str

class Suggestion(BaseModel):
    text:str

class SolveCaseResult(BaseModel):
    suggestions: List[Suggestion]