from pydantic import BaseModel


class Dish(BaseModel):
    dishName: str
    ingredients: list
    recipe: str
    recommendedIngredient: str
    warning: str


class ResponseBody(BaseModel):
    text: str = None
    question: str = None
    chatId: str = None
    chatMessageId: str = None
    isStreamValid: bool = False
    sessionId: str = None
    memoryType: str = None
    statusCode: int = None
    success: bool = True
    message: str = None
