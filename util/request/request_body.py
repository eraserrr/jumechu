from pydantic import BaseModel

class RequestBody(BaseModel):
    ingredients: list[str]