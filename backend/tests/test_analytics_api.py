import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app, lifespan


@pytest.mark.asyncio
async def test_analytics_endpoints():
    async with lifespan(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Summary
            resp = await client.get("/api/analytics/summary")
            assert resp.status_code == 200
            data = resp.json()
            assert "total_requests" in data
            assert "total_tokens_saved" in data
            assert "tokens_saved_actual" in data
            assert "tokens_saved_estimated" in data
            assert "repair_distribution" in data
            assert "model_usage" in data
            assert "compaction" in data

            # 2. Token savings series
            resp = await client.get("/api/analytics/token-savings?limit=10")
            assert resp.status_code == 200
            assert "series" in resp.json()

            # 3. Cache analytics
            resp = await client.get("/api/analytics/cache")
            assert resp.status_code == 200
            cache_data = resp.json()
            assert "total_cache_lookups" in cache_data
            assert "cache_hit_rate" in cache_data

            # 4. Memory analytics
            resp = await client.get("/api/analytics/memory")
            assert resp.status_code == 200
            mem_data = resp.json()
            assert "total_sessions" in mem_data
            assert "context_reduction_pct" in mem_data

            # 5. Exemplar analytics
            resp = await client.get("/api/analytics/exemplars")
            assert resp.status_code == 200
            ex_data = resp.json()
            assert "total_exemplars" in ex_data

            # 6. Compaction analytics
            resp = await client.get("/api/analytics/compaction")
            assert resp.status_code == 200
            comp_data = resp.json()
            assert "compactions_triggered" in comp_data
