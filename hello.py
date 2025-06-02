from fastapi import FastAPI
import requests

API_URL = "http://localhost:3000/api/v1/prediction/e50cc8f1-b857-42bf-88b9-acfef345fb24"

form_data = {}

body_data = {
    "question": """
    내가 가진 재료

[묵은지, 김, 쌀, 스팸, 대파, 당근, 애호박, 참치, 셀러리]

내가 가진 기본 조미료

[소금, 설탕, 후추, 된장, 고추장, 간장, 참기름, 식초, 올리고당, 깨소금, 김치, 식용유]
    """,
    # "chatId": "cada1b46-a7f3-4317-ab6f-3931a0832897",  ## 이전 채팅 아이디를 넣으면 대화를 이어나갈 수 있음
    # "streaming": True
}


def query(form_data, body_data):
    response = requests.post(API_URL,
                             files=form_data,
                             data=body_data
                             )
    return response.json()


## 실행 : uvicorn hello:app --reload

app = FastAPI()


@app.get("/")
def read_hello():
    output = query(form_data, body_data)
    return output
