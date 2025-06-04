import dataclasses

@dataclasses.dataclass
class Dish:
    dishName: str
    ingredients: list
    recipe: str
    recommendedIngredient: str
    warning: str


@dataclasses.dataclass
class ResponseBody:
    text: str
    question: str
    chatId: str
    chatMessageId: str
    isStreamValid: bool
    sessionId: str
    memoryType: str
