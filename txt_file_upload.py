from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import create_retriever_tool
from langchain_core.prompts import PromptTemplate

# 1. 문서 로드
print("📄 문서를 로딩하는 중...")
loader = TextLoader("./document/slowaging01.txt")
document: list[Document] = loader.load()
print(f"✅ 문서 로드 완료: {len(document)}개 문서")

# 2. 문서 분할
print("\n✂️ 문서를 청크로 분할하는 중...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=100,
    add_start_index=True
)
all_split = text_splitter.split_documents(document)
print(f"✅ 분할 완료: {len(all_split)}개 청크")

# 3. 임베딩 및 벡터 스토어 생성
print("\n🔢 임베딩 및 벡터 스토어 생성 중...")
embeddings = OpenAIEmbeddings()
vector_store = InMemoryVectorStore(embeddings)
vector_store.add_documents(documents=all_split)
print(f"✅ 벡터 스토어에 {len(all_split)}개 문서 추가 완료")

# 4. 유사도 검색 테스트
print("\n🔍 유사도 검색 테스트...")
test_query = "제로 콜라는 몸에 좋나요?"
result = vector_store.similarity_search(test_query, k=2)
print(f"쿼리: {test_query}")
for i, doc in enumerate(result):
    print(f"\n[결과 {i+1}]")
    print(doc.page_content[:100] + "...")

# 5. Retriever 생성
print("\n🔧 Retriever 생성 중...")
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

# 6. LLM 및 Tool 설정
print("\n🤖 LLM 및 도구 설정 중...")
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

tool = create_retriever_tool(
    retriever,
    "health_information_retriever",
    "건강 정보를 검색합니다. 제로 콜라, 인공감미료, 노화 등에 관한 정보를 찾을 때 사용하세요.",
)

# 7. Agent 프롬프트 템플릿
template = '''Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

prompt = PromptTemplate.from_template(template)

# 8. Agent 생성 및 실행
print("\n🚀 Agent 생성 중...")
agent = create_react_agent(llm, [tool], prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=[tool],
    verbose=True,
    handle_parsing_errors=True
)

# 9. 질문에 답변
print("\n" + "="*50)
print("💬 질문 답변 시작")
print("="*50)

question = "제로콜라 몸에 좋아요?"
print(f"\n질문: {question}\n")

result = agent_executor.invoke({"input": question})

print("\n" + "="*50)
print("📝 최종 답변")
print("="*50)
print(result["output"])