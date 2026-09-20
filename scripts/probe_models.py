import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY", "").strip("\"'")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

models_to_test = [
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "meta/llama-3.2-11b-vision-instruct",
    "meta/llama-3.2-90b-vision-instruct",
    "nvidia/llama-3.1-nemotron-51b-instruct",
    "nvidia/llama3-chatqa-1.5-70b",
    "ibm/granite-3.0-8b-instruct",
    "databricks/dbrx-instruct"
]

with httpx.Client(timeout=10.0) as client:
    for m in models_to_test:
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5
        }
        res = client.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload)
        print(f"Model: {m:<45} -> Status: {res.status_code}")
        if res.status_code == 200:
            print(f"  [SUCCESS!] Model {m} is active and working!")
            break
