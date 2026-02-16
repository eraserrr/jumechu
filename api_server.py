import json

import requests
import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
from sqlalchemy import join
from sqlalchemy import delete

from database.session import async_session
from entity.ingredient import Ingredient
from entity.user import User
from util.api_uri import AGENT_SERVER_API_URL
from util.base_ingredients import get_base_ingredients
from util.request.agent_request_body import AgentRequestBody
from util.request.request_body import RequestBody

app = FastAPI()

async def get_db():
    async with async_session() as session:
        yield session

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",            # 허용할 출처
    allow_credentials=True,           # 쿠키 포함 여부
    allow_methods=["*"],              # 허용할 HTTP 메소드 (*=모두)
    allow_headers=["*"],              # 허용할 헤더 (*=모두)
)

@app.get("/")
def hello():
   return "Hello World!"

@app.get("/v1/base_ingredients")
def base_ingredients():
    return get_base_ingredients()

@app.get("/v1/{user_id}/ingredients")
async def get_ingredients(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Ingredient)
        .where(and_(User.user_name == user_id))
        .select_from(join(User, Ingredient, User.id == Ingredient.user_id))
    )
    scalars = result.scalars().all()

    return {'ingredients': [Ingredient(id=scalar.id, user_id=scalar.user_id, ingredient_name=scalar.ingredient_name) for scalar in scalars]}

@app.put("/v1/{user_id}/ingredients")
async def update_ingredients(user_id: str, ingredients: dict, db: AsyncSession = Depends(get_db)):
    stmt = await db.execute(
        select(User).where(and_(User.user_name == user_id))
    )
    user = stmt.scalar()

    await db.execute(delete(Ingredient).where(Ingredient.user_id == user.id))
    await db.commit()

    for ingredient in ingredients["ingredients"]:
        db.add(Ingredient(user_id = user.id, ingredient_name = ingredient))
        await db.commit()

    result = await db.execute(
        select(Ingredient)
        .where(and_(User.user_name == user_id))
        .select_from(join(User, Ingredient, User.id == Ingredient.user_id))
    )

    scalars = result.scalars().all()

    return {'ingredients': [Ingredient(id=scalar.id, user_id=scalar.user_id, ingredient_name=scalar.ingredient_name) for scalar in scalars]}

@app.post("/v1/request")
def request(request_body: RequestBody):
    question = get_question(request_body)

    return query(request_body, question)


def get_question(request_body):
    li = request_body.ingredients

    # For more=true requests, pass exclude ingredients as a list
    # The agent server will build the question using session context
    if request_body.more:
        return {"excludeIngredients": request_body.excludeIngredients}

    with open('util/request/agent_request_format.json', 'rb') as file:
        rf = file.read()

    js = json.loads(rf.decode('utf-8'))
    js["ingredients I have"] = li

    return dict(js)


def query(body_data, question):
    data = AgentRequestBody(
        question=str(question),
        more=body_data.more,
        session_id=body_data.session_id
    )

    response = requests.post(
        AGENT_SERVER_API_URL,
        headers={"Content-Type": "application/json"},
        json=data.model_dump(exclude_none=True),
    )
    return response.json()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)