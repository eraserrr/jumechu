import json
from typing import Any

import requests
import uvicorn
from fastapi import FastAPI

from util.api_uri import FLOWISE_SERVER_API_URL
from util.base_ingredients import get_base_ingredients
from util.request.flowise_request_body import FlowiseRequestBody
from util.request.request_body import RequestBody

app = FastAPI()

@app.get("/")
def hello():
   return "Hello World!"

@app.get("/base_ingredients")
def base_ingredients():
    return get_base_ingredients()

@app.get("/v1/{user_id}/ingredients")
def get_ingredients(user_id: str):
    try:
        with open(f"data/{user_id}_ingredients.json", 'r') as fr:
            ingredients = json.load(fr)
    except FileNotFoundError:
        with open(f"data/{user_id}_ingredients.json", 'w') as fw:
            ingredients = {}
            fw.write(json.dumps(ingredients))
    return ingredients

@app.put("/v1/{user_id}/ingredients")
def update_ingredients(user_id: str, ingredients: dict):
    try:
        with open(f"data/{user_id}_ingredients.json", 'w') as fw:
            fw.write(json.dumps(ingredients))
    except FileNotFoundError:
        with open(f"data/{user_id}_ingredients.json", 'w') as fw:
            ingredients = {}
            fw.write(json.dumps(ingredients))
    return ingredients

@app.post("/v1/request")
def request(request_body: RequestBody):
    question = get_question(request_body)

    return query(request_body, question)


def get_question(request_body):
    li = request_body.ingredients

    if request_body.more:
        with open('util/request/flowise_request_additional_format.txt', 'rb') as file:
            rf2: str = file.read().decode('utf-8')
            return rf2.replace('li', ",".join(request_body.excludeIngredients))

    with open('util/request/flowise_request_format.json', 'rb') as file:
        rf = file.read()

    js = json.loads(rf.decode('utf-8'))
    js["ingredients I have"] = li

    return dict(js)


def query(body_data, question):
    data = FlowiseRequestBody(
        question=str(question),
        more=body_data.more,
        chatId=body_data.chatId
    ) if body_data.more else FlowiseRequestBody(
        question=str(question),
    )

    response = requests.post(
        FLOWISE_SERVER_API_URL,
        headers={"Content-Type": "application/json"},
        json=data.model_dump(exclude_none=True),
    )
    return response.json()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)