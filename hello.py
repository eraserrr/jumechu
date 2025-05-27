from fastapi import FastAPI

## 실행 : uvicorn hello:app --reload

app = FastAPI()

@app.get("/hello")
def read_hello():
    return {"message": "Hello, world!"}