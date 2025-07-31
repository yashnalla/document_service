#!/usr/bin/env python3
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

# Start a session
session = requests.Session()

# Step 1: Get CSRF token
login_page = session.get(f"{BASE_URL}/admin/login/")
csrf_token = None

# Extract CSRF token from the response
for line in login_page.text.split('\n'):
    if 'csrfmiddlewaretoken' in line:
        start = line.find('value="') + 7
        end = line.find('"', start)
        csrf_token = line[start:end]
        break

if not csrf_token:
    print("Could not extract CSRF token")
    exit(1)

print(f"CSRF Token: {csrf_token}")

# Step 2: Login
login_data = {
    'username': 'testuser',
    'password': 'testpass123',
    'csrfmiddlewaretoken': csrf_token,
    'next': '/admin/'
}

login_response = session.post(f"{BASE_URL}/admin/login/", data=login_data)
print(f"Login status: {login_response.status_code}")

# Step 3: Create a document
document_data = {
    "title": "My First Document",
    "content": {
        "type": "doc", 
        "content": [
            {
                "type": "paragraph", 
                "content": [
                    {
                        "type": "text", 
                        "text": "Hello World from authenticated user!"
                    }
                ]
            }
        ]
    }
}

# Get CSRF token for API call
api_response = session.get(f"{BASE_URL}/api/documents/")
csrf_token_api = session.cookies.get('csrftoken')

headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf_token_api,
    'Referer': BASE_URL
}

create_response = session.post(
    f"{BASE_URL}/api/documents/",
    data=json.dumps(document_data),
    headers=headers
)

print(f"Create document status: {create_response.status_code}")
print(f"Create document response: {create_response.text}")

# Step 4: List documents
list_response = session.get(f"{BASE_URL}/api/documents/")
print(f"List documents status: {list_response.status_code}")
if list_response.status_code == 200:
    documents = list_response.json()
    print(f"Number of documents: {documents['count']}")