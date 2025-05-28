from fastapi import FastAPI
import requests


API_URL = "https://cloud.flowiseai.com/api/v1/vector/upsert/81c95462-3c10-4695-b877-e2435ddbd1a3"

# use form data to upload files
form_data = {
    "files": ('openAITestFile.txt', open('openAITestFile.txt', 'rb'))
}
body_data = {
    "chunkSize": 1,
    "chunkOverlap": 1,
}

def query(form_data, body_data):
    response = requests.post(API_URL, files=form_data, data=body_data)
    return response.json()

## 실행 : uvicorn hello:app --reload

app = FastAPI()

@app.get("/hello")
def read_hello():
    output = query(form_data, body_data)
    return output