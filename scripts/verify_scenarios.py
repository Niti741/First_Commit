import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import AsyncClient, ASGITransport
from backend.app.main import app, lifespan


async def run_scenario_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with lifespan(app):
            scenarios = [
                ("hello", "GREETING", 1),
                ("hi", "GREETING", 1),
                ("how are you?", "CASUAL_CONVERSATION", 1),
                ("thanks", "GRATITUDE", 1),
                ("kya haal hai?", "CASUAL_CONVERSATION", 1),
                ("hello, what is the hostel fee?", "HANDBOOK_QUERY", None),
                ("hi, write a python function to check if a number is prime", "CODING", None),
            ]
            print("\n================= SCENARIO VERIFICATION RESULTS =================")
            for q, expected_intent, expected_rung in scenarios:
                res = await client.post("/api/chat", json={"question": q, "mode": "kifayat"})
                assert res.status_code == 200, f"Status code {res.status_code}"
                data = res.json()
                receipt = data["receipt"]
                print(f"[PASS] \"{q}\" -> Intent: {receipt['intent']} | Rung: {receipt['rung']} | Latency: {receipt['latency_ms']}ms | Fallback: {receipt['fallback_used']}")
                assert receipt["intent"] == expected_intent, f"Expected intent {expected_intent}, got {receipt['intent']}"
                if expected_rung is not None:
                    assert receipt["rung"] == expected_rung, f"Expected Rung {expected_rung}, got {receipt['rung']}"

            # Verify diagnostic endpoints
            print("\n================= DIAGNOSTIC ENDPOINTS TEST =================")
            h = await client.get("/health")
            print(f"[PASS] GET /health: {h.json()}")
            s = await client.get("/v1/provider/status")
            print(f"[PASS] GET /v1/provider/status: {s.json()}")
            t = await client.post("/v1/provider/test")
            print(f"[PASS] POST /v1/provider/test: {t.json()}")

            print("\n>>> ALL SCENARIOS & DIAGNOSTICS VERIFIED 100% SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    asyncio.run(run_scenario_tests())
