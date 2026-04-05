import requests
import json
import time

def test_health():
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Health Check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health Check Failed: {e}")
        return False

def test_generate_proposal():
    url = "http://localhost:8000/generate_proposal"
    payload = {
        "job_description": "We need a Python developer who is good at FastAPI and LangGraph."
    }
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("Proposal generated successfully!")
            print(f"Status: {result.get('status')}")
            print(f"Grounding Score: {result.get('grounding_score')}")
            # print(f"Proposal Snippet: {result.get('proposal')[:100]}...")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    # Note: This script assumes the server is already running or will be started
    if test_health():
        test_generate_proposal()
    else:
        print("Server is not running. Please start it with 'uvicorn src.app:app --reload'")
