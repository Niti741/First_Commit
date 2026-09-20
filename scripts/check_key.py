import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY", "").strip("\"'")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
model = "mistralai/mistral-7b-instruct-v0.3"
provider = os.getenv("LLM_PROVIDER", "mock")

print(f"Current LLM_PROVIDER in .env : '{provider}'")
print(f"API key detected             : {'YES (starts with ' + api_key[:7] + '...)' if api_key else 'NO'}")
print(f"Key length                   : {len(api_key)} characters")

if not api_key:
    print("\n[!] NVIDIA_API_KEY is empty in .env.")
    exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Hello! Reply with 'NVIDIA API IS WORKING'"}],
    "max_tokens": 15,
    "temperature": 0.1
}


print("\nContacting NVIDIA API endpoint at https://integrate.api.nvidia.com/v1 ...")
try:
    with httpx.Client(timeout=15.0) as client:
        res = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        print(f"HTTP Status Code: {res.status_code}")
        if res.status_code == 200:
            print("\n[SUCCESS] Your NVIDIA API key is VALID and working perfectly!")
            content = res.json()["choices"][0]["message"]["content"]
            print(f"Model response: {content.strip()}")
        elif res.status_code == 401:
            print("\n[ERROR 401] Unauthorized: The API key appears invalid or expired.")
        else:
            print(f"\n[HTTP {res.status_code}] Response:")
            print(res.text)
except Exception as e:
    print(f"\n[NETWORK ERROR] Could not connect to NVIDIA endpoint: {e}")
