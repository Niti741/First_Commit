import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY", "").strip("\"'")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

strong_models = [
    "meta/llama-3.2-90b-vision-instruct",
    "nvidia/llama3-chatqa-1.5-70b",
    "meta/llama2-70b",
    "ibm/granite-3.0-8b-instruct"
]

with httpx.Client(timeout=10.0) as client:
    for m in strong_models:
        payload = {
            "model": m,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5
        }
        res = client.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload)
        print(f"Model: {m:<45} -> Status: {res.status_code}")
