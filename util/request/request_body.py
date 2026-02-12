from pydantic import BaseModel

class RequestBody(BaseModel):
    ingredients: list[str]
    more: bool = False
    excludeIngredients: list[str] = []