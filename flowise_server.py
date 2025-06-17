import json

import requests
import uvicorn
from fastapi import FastAPI

from util.api_uri import FLOWISE_PREDICTION_API_URL
from util.request.flowise_request_body import FlowiseRequestBody
from util.request.prediction_request_body import PredictionRequestBody
from util.response.prediction_response_body import ResponseBody


app = FastAPI()

@app.post("/v1/request")
def chat_ai(request_body: FlowiseRequestBody):
    print(request_body)
    body = PredictionRequestBody(
        question=request_body.question,
        chatId=request_body.chatId,
    ) if request_body.more else PredictionRequestBody(
        question=request_body.question,
    )

    response = requests.post(
        FLOWISE_PREDICTION_API_URL, files={}, data=body.model_dump(exclude_none=True),
    )
    answer = ResponseBody(**response.json())
    if not answer.success:
        return answer.message

    js = json.loads(answer.text)

    return { answer.chatId : js }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)