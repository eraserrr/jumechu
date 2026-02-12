from pydantic import BaseModel

class AgentRequestBody(BaseModel):
    question: str
    more: bool = False