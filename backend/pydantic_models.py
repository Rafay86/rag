from pydantic import BaseModel
from typing import List, Optional

class ChatHistory(BaseModel):
    role: str
    content: str

class QueryInput(BaseModel):
    question: str
    session_id: Optional[str] = None
    history: Optional[List[ChatHistory]] = []

class QueryResponse(BaseModel):
    answer: str
    highlighted_contexts: List[dict]

class DeleteFileRequest(BaseModel):
    file_id: int
