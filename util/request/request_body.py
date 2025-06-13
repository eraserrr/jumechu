from pydantic import BaseModel

class RequestBody(BaseModel):
    ingredients: list[str]
    more: bool = False
    chatId: str = None
    excludeIngredients: list[str] = []