from pydantic import BaseModel
from typing import Optional

class AgentRequestBody(BaseModel):
    question: str
    more: bool = False
    session_id: Optional[str] = None