import json

import requests
from fastapi import FastAPI

from util.request.prediction_request_body import PredictionRequestBody
from util.request.request_body import RequestBody
from util.response.prediction_response_body import ResponseBody

API_URL = "http://localhost:3000/api/v1/prediction/e50cc8f1-b857-42bf-88b9-acfef345fb24"

def query(form_data, body_data):
    response = requests.post(API_URL,
                             files=form_data,
                             data=body_data
                             )
    return response.json()


app = FastAPI()

@app.get("/")
def hello():
   return "Hello World!"

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

    return chat_ai(request_body, question)


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


def chat_ai(request_body, question):
    body = PredictionRequestBody(
        question=str(question),
        chatId=request_body.chatId if request_body.more else None,
    ) if request_body.more else PredictionRequestBody(
        question=str(question),
    )
    js = body.model_dump(exclude_none=True)

    response = requests.post(
        API_URL, files={}, data=js,
    )
    answer = ResponseBody(**response.json())
    if not answer.success:
        return answer.message

    js = json.loads(answer.text)

    return { answer.chatId : js }
