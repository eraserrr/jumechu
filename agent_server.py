import json
import os
import re
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_community.document_loaders import TextLoader
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from util.request.agent_request_body import AgentRequestBody
from util.request.request_body import RequestBody

# .env 파일 로드
load_dotenv()

# LangSmith 설정 확인
print(f"🔍 LangSmith 설정 확인:")
print(f"  LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"  LANGCHAIN_ENDPOINT: {os.getenv('LANGCHAIN_ENDPOINT')}")
print(f"  LANGCHAIN_API_KEY: {'설정됨' if os.getenv('LANGCHAIN_API_KEY') else '없음'}")
print(f"  LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}\n")

app = FastAPI()

# 전역 변수로 벡터 스토어 및 체인 저장
vector_store = None
recipe_chain = None

@tool
def compare_ingredients(user_ingredients: str, recipe_ingredients: str) -> str:
    """
    사용자가 가진 재료와 레시피에 필요한 재료를 비교하여 부족한 재료를 반환합니다.

    Args:
        user_ingredients: 사용자가 가진 재료 목록 (쉼표로 구분된 문자열, 예: "양파, 소시지, 토마토")
        recipe_ingredients: 레시피에 필요한 재료 목록 (쉼표로 구분된 문자열, 예: "카레 가루, 순두부, 토마토 2개, 양파 1/2")

    Returns:
        부족한 재료를 쉼표로 구분한 문자열 (예: "카레 가루, 순두부")
    """
    def normalize_ingredient(ingredient: str) -> str:
        """재료 이름에서 수량/단위 제거하고 정규화"""
        # 숫자, 단위, 특수문자 제거
        normalized = re.sub(r'[\d]+[./\d]*', '', ingredient)  # 숫자 제거
        normalized = re.sub(r'[개모컵큰술작은술g㎖ml]', '', normalized)  # 단위 제거
        normalized = normalized.strip().lower()
        return normalized

    # 문자열을 리스트로 변환
    user_list = [ing.strip() for ing in user_ingredients.split(',')]
    recipe_list = [ing.strip() for ing in recipe_ingredients.split(',')]

    # 사용자 재료를 정규화
    normalized_user = {normalize_ingredient(ing) for ing in user_list}

    # 부족한 재료 찾기
    missing_ingredients = []
    for recipe_ing in recipe_list:
        normalized_recipe = normalize_ingredient(recipe_ing)
        if normalized_recipe and normalized_recipe not in normalized_user:
            missing_ingredients.append(recipe_ing)

    return ", ".join(missing_ingredients) if missing_ingredients else "모든 재료가 있습니다"

def initialize_vector_store():
    """레시피 문서들을 로드하여 벡터 스토어 초기화"""
    global vector_store

    print("📄 레시피 문서들을 로딩하는 중...")

    # document 폴더의 모든 txt 파일 로드
    document_path = Path("./document")
    txt_files = list(document_path.glob("*.txt"))

    if not txt_files:
        print("⚠️ 레시피 문서를 찾을 수 없습니다.")
        return

    all_documents = []
    for txt_file in txt_files:
        try:
            loader = TextLoader(str(txt_file))
            documents = loader.load()
            all_documents.extend(documents)
            print(f"✅ {txt_file.name} 로드 완료")
        except Exception as e:
            print(f"❌ {txt_file.name} 로드 실패: {e}")

    print(f"\n✂️ 총 {len(all_documents)}개 문서를 청크로 분할하는 중...")

    # 문서 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        add_start_index=True
    )
    all_splits = text_splitter.split_documents(all_documents)
    print(f"✅ 분할 완료: {len(all_splits)}개 청크")

    # 벡터 스토어 생성
    print("\n🔢 임베딩 및 벡터 스토어 생성 중...")
    embeddings = OpenAIEmbeddings()
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents=all_splits)
    print(f"✅ 벡터 스토어에 {len(all_splits)}개 문서 추가 완료\n")

def initialize_chain():
    """레시피 추천 체인 초기화"""
    global recipe_chain, vector_store

    if vector_store is None:
        initialize_vector_store()

    print("🤖 레시피 추천 체인 초기화 중...")

    # Retriever 생성 - 더 많은 레시피를 검색
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 10}
    )

    # LLM 설정
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # 시스템 프롬프트
    system_prompt = """당신은 레시피 데이터베이스에서 정확한 레시피를 찾아주는 전문가입니다.

**중요 규칙:**
1. 데이터베이스의 레시피 정보에 있는 레시피만 사용하세요
2. 절대로 레시피를 조합하거나 새로 만들지 마세요
3. 사용자가 입력한 재료가 하나라도 포함된 레시피를 찾으세요
4. 찾은 레시피의 음식 이름, 재료, 조리법을 데이터베이스에 있는 그대로 사용하세요
5. 데이터베이스에 없는 레시피라면, 빈 배열 []을 반환하세요
6. 저속노화 관점에서 주의할 점을 "warning"에 포함하세요

**재료 비교 방법 (매우 중요!):**
7. 반드시 compare_ingredients tool을 사용하여 부족한 재료를 찾으세요
8. tool 사용 시:
   - user_ingredients: 사용자가 가진 재료를 쉼표로 구분한 문자열 (예: "양파, 소시지, 토마토")
   - recipe_ingredients: 선택한 레시피의 모든 재료를 쉼표로 구분한 문자열
9. tool의 결과를 그대로 "recommendedIngredient"에 넣으세요

**반드시 아래 JSON 형식으로만 응답하세요 (다른 설명 없이 JSON만):**

[{{
  "dishName": "데이터베이스에 있는 정확한 음식 이름",
  "ingredients": ["데이터베이스에 있는 정확한 재료 목록"],
  "recipe": "데이터베이스에 있는 정확한 조리법",
  "recommendedIngredient": "compare_ingredients tool의 결과",
  "warning": "저속노화 관점의 주의사항"
}}]"""

    # Agent 생성 - RAG와 Tool을 함께 사용
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Retriever를 tool로 만들기
    @tool
    def search_recipes(query: str) -> str:
        """레시피 데이터베이스에서 관련 레시피를 검색합니다."""
        docs = retriever.invoke(query)
        return format_docs(docs)

    # Agent 생성
    agent = create_react_agent(
        llm,
        [search_recipes, compare_ingredients]
    )

    # 시스템 프롬프트를 포함한 래퍼 함수
    def recipe_chain_wrapper(input_data):
        from langchain_core.messages import SystemMessage, HumanMessage

        # 사용자 메시지 추출
        if isinstance(input_data, dict) and "messages" in input_data:
            user_msg = input_data["messages"][0][1]
        else:
            user_msg = input_data

        # 시스템 메시지 + 사용자 메시지로 Agent 호출
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg)
        ]

        return agent.invoke({"messages": messages})

    recipe_chain = recipe_chain_wrapper

    print("✅ 체인 초기화 완료\n")


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 벡터 스토어 및 체인 초기화"""
    initialize_vector_store()
    initialize_chain()


@app.get("/")
def hello():
    return {"message": "Recipe Recommendation API with Vector DB"}


def parse_recipe_response(output: str):
    """에이전트 응답에서 JSON 추출"""
    try:
        # JSON 부분만 추출 (```json 태그가 있을 수 있음)
        start_idx = output.find('[')
        end_idx = output.rfind(']') + 1

        if start_idx != -1 and end_idx > start_idx:
            json_str = output[start_idx:end_idx]
            return json.loads(json_str)

        # JSON 형식이 아니면 원본 반환
        return {"raw_answer": output}
    except Exception as e:
        print(f"⚠️ JSON 파싱 실패: {e}")
        return {"raw_answer": output}

@app.post("/v1/request")
@traceable(name="chat_ai_endpoint", run_type="chain")
def chat_ai(request_body: AgentRequestBody):
    """사용자 질문에 대해 레시피 추천"""
    global recipe_chain

    if recipe_chain is None:
        return {"error": "Recipe chain is not initialized"}

    print(f"\n{'=' * 50}")
    print(f"💬 질문: {request_body.question}")
    print(f"{'=' * 50}\n")

    try:
        result = recipe_chain(request_body.question)
        # Agent의 최종 메시지 추출
        final_message = result["messages"][-1].content
        parsed_answer = parse_recipe_response(final_message)

        response = {
            "answer": parsed_answer
        }

        return response

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/v1/recipe")
@traceable(name="recommend_recipe_endpoint", run_type="chain")
def recommend_recipe(request_body: RequestBody):
    """재료 기반 레시피 추천"""
    global recipe_chain

    if recipe_chain is None:
        return {"error": "Recipe chain is not initialized"}

    # 재료 목록으로 질문 생성
    ingredients_str = ", ".join(request_body.ingredients)

    question = f"다음 재료들로 만들 수 있는 건강한 레시피를 추천해주세요: {ingredients_str}"

    # 제외할 재료가 있다면 추가
    if request_body.excludeIngredients:
        exclude_str = ", ".join(request_body.excludeIngredients)
        question += f"\n단, 다음 재료는 사용하지 마세요: {exclude_str}"

    print(f"\n{'=' * 50}")
    print(f"💬 질문: {question}")
    print(f"{'=' * 50}\n")

    try:
        result = recipe_chain(question)
        # Agent의 최종 메시지 추출
        final_message = result["messages"][-1].content
        parsed_answer = parse_recipe_response(final_message)

        response = {
            "answer": parsed_answer
        }

        return response

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
