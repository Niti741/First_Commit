import pytest
from backend.app.context.canonicalizer import Canonicalizer
from backend.app.context.builder import ContextBuilder


def test_canonicalizer_normalizes_whitespace():
    dirty_text = "Line 1   \r\n\r\n\r\nLine 2  \t\r\n\r\nLine 3   "
    clean = Canonicalizer.canonicalize_text(dirty_text)
    assert "\r" not in clean
    assert "Line 1\n\nLine 2\n\nLine 3" == clean


def test_prefix_hash_deterministic():
    text1 = "System Instructions\nHandbook details"
    text2 = "System Instructions\r\nHandbook details  "
    hash1 = Canonicalizer.compute_prefix_hash(text1)
    hash2 = Canonicalizer.compute_prefix_hash(text2)
    assert hash1 == hash2


def test_context_builder_checkpoints():
    builder = ContextBuilder()
    prompt_data = builder.build_prompt(
        current_question="What is the hostel fee?",
        recent_raw_turns=[{"role": "user", "content": "Hello"}],
        frozen_blocks=[{"block_id": 1, "summary": "Turn summary", "level": 0}],
        exemplars=[{"question": "Q1", "answer": "A1"}],
        mode="kifayat"
    )

    system_prompt = prompt_data["system"]
    assert "<!-- CACHE_CHECKPOINT_1 -->" in system_prompt
    assert "<!-- CACHE_CHECKPOINT_2 -->" in system_prompt

    # Verify exemplars are placed after checkpoints in user message
    messages = prompt_data["messages"]
    last_msg = messages[-1]["content"]
    assert "=== REFERENCE EXAMPLES (EXEMPLARS) ===" in last_msg
    assert "What is the hostel fee?" in last_msg
