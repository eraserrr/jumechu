# 저메추
저속노화메뉴추천


## 기능 요구 사항 
- 건강한 저녁 식단을 소개해준다
- 내 냉장고 안에 있는 식품을 위주로 소개해준다
- 추가로 사야될게 있다면 알려준다 
- 내 냉장고 안에 있는 식품을 저장한다
- 내 냉장고 안에 있는 식품을 쉽게 뺄 수 있다.
- 칼로리도 알려준다

## 비기능 요구 사항
- 냉장고 안에 있는 식품을 데이터 베이스에 저장한다
- 웹 서버만 동작한다 (모바일 불가)




----

가상환경 실행

```shell
source .venv/bin/activate
```

레디스 초기 실행

```shell
docker pull redis
docker run redis --name redis -p 6379:6379 
```

flowise 실행

```shell
npx flowise start 
```

api 서버 실행

```shell
uvicorn api_server:app --reload --port 8000
```

flowise 서버 실행

```shell
uvicorn flowise_server:app --reload --port 8080
```