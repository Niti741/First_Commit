import pytest
from backend.app.providers.mock_provider import MockProvider
from backend.app.providers.factory import get_llm_provider


@pytest.mark.asyncio
async def test_mock_provider_generation():
    provider = MockProvider()
    res = await provider.generate(
        messages=[{"role": "user", "content": "What is the hostel fee?"}],
        system="System instructions"
    )
    assert res.text is not None
    assert len(res.text) > 20
    assert "42,000" in res.text or "hostel" in res.text.lower()
    assert res.usage.input_tokens > 0
    assert res.usage.output_tokens > 0


@pytest.mark.asyncio
async def test_mock_provider_hinglish():
    provider = MockProvider()
    res = await provider.generate(
        messages=[{"role": "user", "content": "Hostel ka fee kitna hai?"}]
    )
    assert any(w in res.text.lower() for w in ["kit", "hostel", "42,000", "per semester", "room"])


@pytest.mark.asyncio
async def test_mock_provider_streaming():
    provider = MockProvider()
    chunks = []
    async for chunk in provider.stream(
        messages=[{"role": "user", "content": "Attendance rules?"}]
    ):
        chunks.append(chunk)
    combined = "".join(chunks)
    assert len(combined) > 20
    assert "attendance" in combined.lower() or "75%" in combined


@pytest.mark.asyncio
async def test_mock_provider_embeddings():
    provider = MockProvider()
    embeddings = await provider.embed(["Hostel fee", "How much does hostel cost?", "Quantum physics"])
    assert len(embeddings) == 3
    assert len(embeddings[0]) == 384

    # Test semantic similarity between paraphrases
    import numpy as np
    v0 = np.array(embeddings[0])
    v1 = np.array(embeddings[1])
    v2 = np.array(embeddings[2])

    sim_paraphrase = float(np.dot(v0, v1))
    sim_unrelated = float(np.dot(v0, v2))

    assert sim_paraphrase > 0.80
    assert sim_paraphrase > sim_unrelated


@pytest.mark.asyncio
async def test_mock_provider_judge():
    provider = MockProvider()
    res_pass = await provider.judge(
        question="Hostel fee?",
        answer="Single occupancy room fee is ₹42,000 per semester.",
        context="Single Occupancy: ₹42,000"
    )
    assert res_pass.passed is True
    assert res_pass.score >= 4

    res_fail = await provider.judge(
        question="What is the hostel fee?",
        answer="I cannot answer this question.",
        context=""
    )
    assert res_fail.passed is False
