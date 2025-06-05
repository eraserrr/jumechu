from pydantic import BaseModel

class PredictionRequestBody(BaseModel):
    question: str
    chatId: str = None
    streaming: bool = None