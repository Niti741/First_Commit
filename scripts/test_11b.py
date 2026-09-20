import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY", "").strip("\"'")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "meta/llama-3.2-11b-vision-instruct",
    "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
    "max_tokens": 10
}

with httpx.Client(timeout=25.0) as client:
    res = client.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload)
    print("Status:", res.status_code)
    if res.status_code == 200:
        print("Model answer:", res.json()["choices"][0]["message"]["content"])
    else:
        print("Error:", res.text)
