from fastapi import FastAPI
import requests


API_URL = "http://localhost:3000/api/v1/prediction/356e2f18-a6b1-4e3d-8638-132f109d4dd2"

# use form data to upload files
form_data = {
    "files": ('openAITestFile.txt', open('openAITestFile.txt', 'rb'))
}
body_data = {"question": "complete the sentence (what's wrong ____ _?)"}

def query(form_data, body_data):
    response = requests.post(API_URL, files=form_data, data=body_data)
    return response.json()

## 실행 : uvicorn hello:app --reload

app = FastAPI()

@app.get("/hello")
def read_hello():
    output = query(form_data, body_data)
    return output