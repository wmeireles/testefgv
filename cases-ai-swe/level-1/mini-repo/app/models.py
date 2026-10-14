# models , request/response schemas
from typing import Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    segment: Optional[str] = None   # metadata filter , see Task 2
    client: Optional[str] = None    # metadata filter , see Task 2


class SearchHit(BaseModel):
    doc_id: str
    score: float
    segment: str
    client: str
    text: str
