import requests

API_URL = "http://localhost:3000/api/v1/vector/upsert/356e2f18-a6b1-4e3d-8638-132f109d4dd2"

# use form data to upload files
form_data = {
    "files": ('openAITestFile.txt', open('openAITestFile.txt', 'rb'))
}

body_data = {
    "returnSourceDocuments": True
}

def query(form_data):
    response = requests.post(API_URL, files=form_data, data=body_data)
    print(response)
    return response.json()

output = query(form_data)
print(output)