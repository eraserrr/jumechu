import json
import glob
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from util.request.agent_request_body import AgentRequestBody
from util.request.request_body import RequestBody

app = FastAPI()

# 전역 변수로 벡터 스토어 및 체인 저장
vector_store = None
recipe_chain = None

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

    # Retriever 생성
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}
    )

    # LLM 설정
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    # 프롬프트 템플릿
    template = """당신은 건강한 레시피를 추천하는 전문가입니다.

사용자 질문: {question}

관련 레시피 정보:
{context}

위 정보를 참고하여, 사용자가 가진 재료로 만들 수 있는 건강한 레시피를 추천해주세요.

**중요 규칙:**
1. 사용자가 가진 재료를 최대한 활용하세요
2. 건강에 좋은 레시피를 우선 추천하세요
3. 레시피는 구체적으로 단계별로 설명하세요
4. 재료가 부족하면 대체 재료를 제안하세요
5. 저속노화 관점에서 주의할 점을 반드시 포함하세요

**반드시 아래 JSON 형식으로만 응답하세요 (다른 설명 없이 JSON만):**

[{{
  "dishName": "음식 이름",
  "ingredients": ["재료1", "재료2", "재료3"],
  "recipe": "1. 첫번째 단계\\n2. 두번째 단계\\n3. 세번째 단계",
  "recommendedIngredient": "(예: 당근, 브로콜리)",
  "warning": "(예: 혈당 관리, 염증 유발 성분 등)"
}}]"""

    prompt = PromptTemplate.from_template(template)

    # 체인 생성 - RAG 패턴 사용
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    recipe_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

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
def chat_ai(request_body: AgentRequestBody):
    """사용자 질문에 대해 레시피 추천"""
    global recipe_chain

    if recipe_chain is None:
        return {"error": "Recipe chain is not initialized"}

    print(f"\n{'='*50}")
    print(f"💬 질문: {request_body.question}")
    print(f"{'='*50}\n")

    try:
        result = recipe_chain.invoke(request_body.question)
        parsed_answer = parse_recipe_response(result)

        response = {
            "answer": parsed_answer
        }

        return response

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return {"error": str(e)}

@app.post("/v1/recipe")
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

    print(f"\n{'='*50}")
    print(f"💬 질문: {question}")
    print(f"{'='*50}\n")

    try:
        result = recipe_chain.invoke(question)
        parsed_answer = parse_recipe_response(result)

        response = {
            "answer": parsed_answer
        }

        return response

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)