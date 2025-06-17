from pydantic import BaseModel

class FlowiseRequestBody(BaseModel):
    question: str
    more: bool = False
    chatId: str = None