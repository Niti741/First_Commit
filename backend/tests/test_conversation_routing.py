import json
import os
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.router import ConversationIntentClassifier, IntentType
from backend.app.models.schemas import KifayatReceipt
from backend.app.main import app, lifespan
from backend.app.storage.sqlite_store import SQLiteStore
from backend.app.providers.mock_provider import MockProvider
from backend.app.context.builder import ContextBuilder
from backend.app.cache.local_cache import LocalSemanticCache
from backend.app.exemplars.store import ExemplarStore
from backend.app.memory.compaction_queue import LocalCompactionQueue
from backend.app.gateway import KifayatGateway


@pytest.fixture
def eval_dataset():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "eval", "conversation_examples.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_intent_classifier_on_full_eval_dataset(eval_dataset):
    """Verify that all 56 evaluation examples classify accurately."""
    examples = eval_dataset["examples"]
    assert len(examples) >= 50, "Dataset must have at least 50 examples"

    for ex in examples:
        res = ConversationIntentClassifier.classify(ex["text"])
        assert res.intent.value == ex["expected_intent"], (
            f"Failed for text '{ex['text']}': expected {ex['expected_intent']}, got {res.intent.value}"
        )
        assert res.is_conversational == ex["expected_is_conversational"], (
            f"Failed is_conversational for '{ex['text']}': expected {ex['expected_is_conversational']}, got {res.is_conversational}"
        )
        assert res.maximum_rung == ex["expected_max_rung"], (
            f"Failed max_rung for '{ex['text']}': expected {ex['expected_max_rung']}, got {res.maximum_rung}"
        )


@pytest.mark.asyncio
async def test_hello_routes_to_rung_1_fast_path(tmp_path):
    """Verify 'hello' strictly stays on Rung 1 and does not escalate to Rung 3."""
    db_path = str(tmp_path / "test_gateway.db")
    store = SQLiteStore(db_path=db_path)
    context_builder = ContextBuilder()
    provider = MockProvider(handbook_text=context_builder.canonical_handbook)
    cache = LocalSemanticCache(db_path=db_path)
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    queue = LocalCompactionQueue(session_store=store)

    gateway = KifayatGateway(
        store=store,
        provider=provider,
        context_builder=context_builder,
        semantic_cache=cache,
        exemplar_store=exemplar_store,
        compaction_queue=queue
    )

    result = await gateway.process_chat(question="hello", session_id="test-hello-sess")
    assert "text" in result
    receipt = result["receipt"]

    assert receipt.rung == 1, f"Expected Rung 1 for 'hello', got Rung {receipt.rung}"
    assert receipt.intent == "GREETING"
    assert "conversational greeting" in (receipt.routing_reason or "").lower()
    assert receipt.node_states.get("semantic_cache") == "SKIPPED"
    assert receipt.node_states.get("cheap_model") == "COMPLETED"
    assert receipt.node_states.get("rung3_strong") == "SKIPPED"
    assert receipt.node_states.get("rung2_exemplars") == "SKIPPED"
    assert receipt.judge_score == 5
    assert not receipt.fallback_used


@pytest.mark.asyncio
async def test_conversational_queries_stay_on_rung_1(tmp_path):
    """Verify greetings, pleasantries, gratitude, and farewells all remain on Rung 1."""
    db_path = str(tmp_path / "test_gateway_conv.db")
    store = SQLiteStore(db_path=db_path)
    context_builder = ContextBuilder()
    provider = MockProvider(handbook_text=context_builder.canonical_handbook)
    cache = LocalSemanticCache(db_path=db_path)
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    queue = LocalCompactionQueue(session_store=store)

    gateway = KifayatGateway(
        store=store,
        provider=provider,
        context_builder=context_builder,
        semantic_cache=cache,
        exemplar_store=exemplar_store,
        compaction_queue=queue
    )

    test_queries = [
        ("hi", "GREETING"),
        ("how are you?", "CASUAL_CONVERSATION"),
        ("thanks", "GRATITUDE"),
        ("bye", "FAREWELL"),
        ("kya haal hai?", "CASUAL_CONVERSATION"),
        ("shukriya", "GRATITUDE")
    ]

    for q, expected_intent in test_queries:
        res = await gateway.process_chat(question=q, session_id=f"test-sess-{q[:4]}")
        receipt = res["receipt"]
        assert receipt.rung == 1, f"Query '{q}' escalated to Rung {receipt.rung}!"
        assert receipt.intent == expected_intent, f"Query '{q}' had intent {receipt.intent}, expected {expected_intent}"
        assert receipt.node_states.get("rung3_strong") == "SKIPPED"


@pytest.mark.asyncio
async def test_embedded_handbook_question_takes_path_b(tmp_path):
    """Verify 'hello, what is the hostel fee?' triggers handbook path rather than pure greeting."""
    db_path = str(tmp_path / "test_gateway_handbook.db")
    store = SQLiteStore(db_path=db_path)
    context_builder = ContextBuilder()
    provider = MockProvider(handbook_text=context_builder.canonical_handbook)
    cache = LocalSemanticCache(db_path=db_path)
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    queue = LocalCompactionQueue(session_store=store)

    gateway = KifayatGateway(
        store=store,
        provider=provider,
        context_builder=context_builder,
        semantic_cache=cache,
        exemplar_store=exemplar_store,
        compaction_queue=queue
    )

    res = await gateway.process_chat(
        question="hello, what is the hostel fee?",
        session_id="test-handbook-sess"
    )
    receipt = res["receipt"]
    assert receipt.intent == "HANDBOOK_QUERY"
    assert "42,000" in res["text"] or "hostel" in res["text"].lower()


@pytest.mark.asyncio
async def test_embedded_coding_question_takes_path_b(tmp_path):
    """Verify 'hi, write a python function to check palindrome' triggers coding path."""
    db_path = str(tmp_path / "test_gateway_code.db")
    store = SQLiteStore(db_path=db_path)
    context_builder = ContextBuilder()
    provider = MockProvider(handbook_text=context_builder.canonical_handbook)
    cache = LocalSemanticCache(db_path=db_path)
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    queue = LocalCompactionQueue(session_store=store)

    gateway = KifayatGateway(
        store=store,
        provider=provider,
        context_builder=context_builder,
        semantic_cache=cache,
        exemplar_store=exemplar_store,
        compaction_queue=queue
    )

    res = await gateway.process_chat(
        question="hi, write a python function to check if a string is a palindrome",
        session_id="test-code-sess"
    )
    receipt = res["receipt"]
    assert receipt.intent == "CODING"
    assert "```" in res["text"]


@pytest.mark.asyncio
async def test_diagnostics_endpoints():
    """Verify /health, /v1/provider/status, and /v1/provider/test work without leaking secrets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with lifespan(app):
            # 1. GET /health
            h_res = await client.get("/health")
            assert h_res.status_code == 200
            h_data = h_res.json()
            assert h_data["status"] == "ok"
            assert "provider" in h_data
            assert "configured" in h_data
            assert "nvapi-" not in json.dumps(h_data)

            # 2. GET /v1/provider/status
            s_res = await client.get("/v1/provider/status")
            assert s_res.status_code == 200
            s_data = s_res.json()
            assert "provider" in s_data
            assert "cheap_model" in s_data
            assert "configured" in s_data
            assert "nvapi-" not in json.dumps(s_data)

            # 3. POST /v1/provider/test
            t_res = await client.post("/v1/provider/test")
            assert t_res.status_code == 200
            t_data = t_res.json()
            assert "status" in t_data
            assert "latency_ms" in t_data
            assert "nvapi-" not in json.dumps(t_data)
