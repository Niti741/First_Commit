import pytest
from backend.app.providers.router import MultiProviderRouter
from backend.app.providers.mock_provider import MockProvider


@pytest.mark.asyncio
async def test_multi_provider_router_basic():
    mock1 = MockProvider()
    mock2 = MockProvider()
    router = MultiProviderRouter(
        providers={"primary": mock1, "secondary": mock2},
        priority_order=["primary", "secondary"]
    )
    
    assert router.provider_name == "multi_provider_router"
    status = router.get_provider_status()
    assert "primary" in status
    assert "secondary" in status
    assert status["primary"]["available"] is True

    res = await router.generate([{"role": "user", "content": "What is 2+2"}])
    assert res.text is not None


@pytest.mark.asyncio
async def test_multi_provider_router_failover():
    class FailingProvider(MockProvider):
        async def generate(self, *args, **kwargs):
            raise ConnectionError("Primary provider connection timeout")

    fail_primary = FailingProvider()
    healthy_secondary = MockProvider()

    router = MultiProviderRouter(
        providers={"primary_failing": fail_primary, "secondary_healthy": healthy_secondary},
        priority_order=["primary_failing", "secondary_healthy"]
    )

    # Should transparently fail over to secondary
    res = await router.generate([{"role": "user", "content": "What is 2+2"}])
    assert res.text is not None
    status = router.get_provider_status()
    assert status["primary_failing"]["consecutive_failures"] == 1
    assert status["secondary_healthy"]["total_calls"] == 1
