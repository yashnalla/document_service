#!/usr/bin/env python3
import requests
import json

# Simple test without authentication (if permissions allow)
BASE_URL = "http://localhost:8000"

# Test document creation without auth
document_data = {
    "title": "Test Document No Auth",
    "content": {
        "type": "doc", 
        "content": [
            {
                "type": "paragraph", 
                "content": [
                    {
                        "type": "text", 
                        "text": "This should fail due to authentication requirement"
                    }
                ]
            }
        ]
    }
}

headers = {'Content-Type': 'application/json'}

response = requests.post(
    f"{BASE_URL}/api/documents/",
    data=json.dumps(document_data),
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# Show how to list documents (this should work without auth)
list_response = requests.get(f"{BASE_URL}/api/documents/")
print(f"\nList Status: {list_response.status_code}")
if list_response.status_code == 200:
    documents = list_response.json()
    print(f"Number of documents: {documents['count']}")
    print("Document titles:", [doc['title'] for doc in documents['results']])