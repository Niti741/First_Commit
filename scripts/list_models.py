import os
import httpx
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY", "").strip("\"'")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

with httpx.Client(timeout=15.0) as client:
    res = client.get(f"{base_url}/models", headers=headers)
    if res.status_code == 200:
        models = [m["id"] for m in res.json().get("data", [])]
        instruct = [m for m in models if "instruct" in m.lower() or "chat" in m.lower()]
        print(f"Total models available: {len(models)}")
        print("Available Instruct/Chat models:")
        for m in sorted(instruct):
            print(f" - {m}")
    else:
        print(f"Status {res.status_code}: {res.text}")

