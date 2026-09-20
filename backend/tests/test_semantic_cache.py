import pytest
import tempfile
import os
import time
from backend.app.cache.local_cache import LocalSemanticCache
from backend.app.cache.safety import CacheSafetyValidator
from backend.app.providers.mock_provider import MockProvider


@pytest.mark.asyncio
async def test_semantic_cache_hit_and_miss():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        cache = LocalSemanticCache(db_path=db_path)
        provider = MockProvider()

        q1 = "What is the hostel fee?"
        q2 = "How much does hostel cost?"
        q3 = "Who won the World Cup in 1983?"

        embs = await provider.embed([q1, q2, q3])

        # Cache miss initially
        miss = await cache.get_similar(q1, embs[0], namespace="test:v1:en")
        assert miss is None

        # Insert q1
        await cache.set(
            question=q1,
            answer="Hostel fee is ₹42,000 for single occupancy.",
            embedding=embs[0],
            namespace="test:v1:en",
            context_hash="hash123",
            ttl=3600
        )

        # Exact hit
        hit1 = await cache.get_similar(q1, embs[0], namespace="test:v1:en", threshold=0.90)
        assert hit1 is not None
        assert "₹42,000" in hit1["answer"]
        assert hit1["similarity"] >= 0.99

        # Semantic paraphrase hit (q2)
        hit2 = await cache.get_similar(q2, embs[1], namespace="test:v1:en", threshold=0.80)
        assert hit2 is not None
        assert "₹42,000" in hit2["answer"]

        # Below threshold miss (q3)
        miss3 = await cache.get_similar(q3, embs[2], namespace="test:v1:en", threshold=0.90)
        assert miss3 is None

        # Namespace isolation: same query, different namespace -> miss
        ns_miss = await cache.get_similar(q1, embs[0], namespace="test:v2:hinglish", threshold=0.90)
        assert ns_miss is None

        # Invalidation
        deleted = await cache.invalidate("test:v1:en")
        assert deleted == 1
        assert await cache.get_similar(q1, embs[0], namespace="test:v1:en") is None

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass



def test_cache_safety_validator():
    # Cacheable
    assert CacheSafetyValidator.is_cacheable("What is the hostel fee per semester?") is True
    assert CacheSafetyValidator.is_cacheable("Exam attendance rules kya hain?") is True

    # Unsafe - personalized
    assert CacheSafetyValidator.is_cacheable("What is my roll number?") is False
    assert CacheSafetyValidator.is_cacheable("Mera hostel balance kitna bacha hai?") is False

    # Unsafe - real time
    assert CacheSafetyValidator.is_cacheable("What is today's schedule?") is False
    assert CacheSafetyValidator.is_cacheable("Aaj classes hain kya?") is False

    # Unsafe - conversational filler / short
    assert CacheSafetyValidator.is_cacheable("ok") is False
    assert CacheSafetyValidator.is_cacheable("yes") is False
