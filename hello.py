from fastapi import FastAPI
import requests

API_URL = "http://localhost:3000/api/v1/prediction/356e2f18-a6b1-4e3d-8638-132f109d4dd2"

form_data = {}

body_data = {
    "question": "알았어 고마워",
    "chatId": "cada1b46-a7f3-4317-ab6f-3931a0832897",  ## 이전 채팅 아이디를 넣으면 대화를 이어나갈 수 있음
    "streaming": True
}


def query(form_data, body_data):
    response = requests.post(API_URL,
                             files=form_data,
                             data=body_data
                             )
    return response.json()


## 실행 : uvicorn hello:app --reload

app = FastAPI()


@app.get("/hello")
def read_hello():
    output = query(form_data, body_data)
    return output
