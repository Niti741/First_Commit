import pytest
from backend.app.context.builder import ContextBuilder
from backend.app.providers.mock_provider import MockProvider
from backend.app.storage.sqlite_store import SQLiteStore
from backend.app.exemplars.store import ExemplarStore
from backend.app.repair.ladder import PromptRepairLadder
from backend.app.repair.rule_checks import CheapRuleChecker
import tempfile
import os


def test_cheap_rule_checker():
    # Valid
    valid, msg = CheapRuleChecker.check_answer("The hostel fee for single occupancy is ₹42,000 per semester.")
    assert valid is True

    # Empty
    empty, _ = CheapRuleChecker.check_answer("")
    assert empty is False

    # Punctuation only / No alphanumeric content
    short, _ = CheapRuleChecker.check_answer("... --- ...")
    assert short is False

    # Refusal
    refusal, _ = CheapRuleChecker.check_answer("As an AI language model, I do not have access to real-time information.")
    assert refusal is False


@pytest.mark.asyncio
async def test_repair_ladder_flow():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name

    try:
        store = SQLiteStore(db_path=db_path)
        provider = MockProvider()
        context_builder = ContextBuilder()
        exemplar_store = ExemplarStore(storage=store, provider=provider)
        await exemplar_store.seed_defaults()

        ladder = PromptRepairLadder(
            provider=provider,
            context_builder=context_builder,
            exemplar_store=exemplar_store
        )

        res = await ladder.execute(
            question="What is the hostel fee?",
            session_context={"raw_turns": [], "frozen_blocks": [], "merged_blocks": []},
            mode="kifayat"
        )

        assert res.text is not None
        assert res.rung in [1, 2, 3]
        assert res.input_tokens > 0
        assert res.judge_score is not None

    finally:
        try:
            if os.path.exists(db_path):
                os.remove(db_path)
        except OSError:
            pass

