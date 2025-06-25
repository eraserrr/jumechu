from io import BytesIO

import requests
import os
import json

API_URL = "http://localhost:3000/api/v1/vector/upsert/e50cc8f1-b857-42bf-88b9-acfef345fb24"


def collect_slowaging_texts(directory_path):
    slowaging_texts = []

    # 디렉토리 내 파일 탐색
    for filename in os.listdir(directory_path):
        if filename.startswith("slowaging") and filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read().strip()
                slowaging_texts.append(content)

    # 딕셔너리 구조로 변환
    result = {
        "저속노화": slowaging_texts
    }

    return result

json_data = json.dumps(collect_slowaging_texts("document"), ensure_ascii=False).encode("utf-8")
form_data = {
    "files": ('slowaging.json', BytesIO(json_data))
}

def query(form_data):
    response = requests.post(API_URL, files=form_data, data=body_data)
    print(response)
    return response.json()

body_data = {
    "returnSourceDocuments": True
}

print(form_data)

output = query(form_data)
print(output)