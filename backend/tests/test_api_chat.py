import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app, lifespan


@pytest.mark.asyncio
async def test_health_endpoint():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/health")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "healthy"
            assert data["project"] == "Kifayat"


@pytest.mark.asyncio
async def test_chat_completions_non_streaming():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "messages": [{"role": "user", "content": "What is the hostel fee?"}],
                "stream": False,
                "mode": "kifayat"
            }
            res = await client.post("/v1/chat/completions", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert "choices" in data
            assert len(data["choices"]) > 0
            assert "kifayat_receipt" in data
            receipt = data["kifayat_receipt"]
            assert receipt["request_id"] is not None
            assert receipt["saving_pct"] >= 0.0


@pytest.mark.asyncio
async def test_chat_completions_streaming():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "messages": [{"role": "user", "content": "Attendance rules?"}],
                "stream": True,
                "mode": "kifayat"
            }
            res = await client.post("/v1/chat/completions", json=payload)
            assert res.status_code == 200
            assert "text/event-stream" in res.headers.get("content-type", "")
            content = res.text
            assert "event: metadata" in content
            assert "event: token" in content
            assert "event: complete" in content


@pytest.mark.asyncio
async def test_dashboard_stats_and_feedback():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Check stats
            res = await client.get("/api/dashboard/stats")
            assert res.status_code == 200
            stats = res.json()
            assert "total_requests" in stats
            assert "cache_hit_rate" in stats

            # Submit feedback
            fb_res = await client.post("/v1/feedback", json={
                "request_id": "req-test-1",
                "question": "What is the library timing during exams?",
                "answer": "Tagore Central Library is open 24x7 during exam weeks.",
                "thumbs_up": True,
                "category": "library"
            })
            assert fb_res.status_code == 200
            fb_data = fb_res.json()
            assert fb_data["status"] == "success"
            assert fb_data["promoted_to_exemplar"] is True
