import json

import requests

API_URL = "http://localhost:3000/api/v1/vector/upsert/e50cc8f1-b857-42bf-88b9-acfef345fb24"

# use form data to upload files
form_data = {
    "files": ('info.txt', open('document/slowaging01.json', 'rb'))
}

body_data = {
    "stopNodeId": "simpleStoreLlamaIndex_0",
    "returnSourceDocuments": True
}

def query(form_data):
    response = requests.post(API_URL, files=form_data, data=body_data)
    print(response)
    return response.json()

output = query(form_data)
print(output)