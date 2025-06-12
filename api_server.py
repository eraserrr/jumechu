import json
from collections import OrderedDict

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

@app.post("/request")
def request(request_body: RequestBody):

    question = get_question(request_body)

    print(question)

    return chat_ai(dict(question))


def get_question(request_body):
    li = request_body.ingredients
    with open('util/request/flowise_request_format.json', 'rb') as file:
        rf = file.read()

    js = json.loads(rf.decode('utf-8'))
    js["ingredients I have"] = li

    return js


def chat_ai(question: dict):
    response = requests.post(
        API_URL, files={}, data=PredictionRequestBody(question=str(question)).model_dump(exclude_none=True),
    )
    answer = ResponseBody(**response.json())
    if not answer.success:
        return answer.message
    return json.loads(answer.text)
