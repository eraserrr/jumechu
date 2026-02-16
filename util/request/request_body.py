from pydantic import BaseModel
from typing import Optional

class RequestBody(BaseModel):
    ingredients: list[str]
    more: bool = False
    excludeIngredients: list[str] = []
    session_id: Optional[str] = None