import pytest
from backend.app.memory.block_manager import BlockManager
from backend.app.memory.hierarchical import HierarchicalMemoryMerger
from backend.app.memory.budget import MemoryBudgetManager


def test_raw_window_and_block_freezing():
    manager = BlockManager(raw_window_turns=2, block_turns=3)
    session = {"raw_turns": [], "frozen_blocks": [], "turn_count": 0}

    # Add 4 turns (less than raw_window + block_turns = 5)
    for i in range(1, 5):
        res = manager.add_turn(session, f"User Q{i}", f"Assistant A{i}")
        session = res["session_data"]
        assert res["pending_freeze_block"] is None

    # Add 5th turn (now 5 turns total -> triggers freeze of oldest 3 turns)
    res = manager.add_turn(session, "User Q5", "Assistant A5")
    pending = res["pending_freeze_block"]
    assert pending is not None
    assert pending["block_id"] == 1
    assert len(pending["turns"]) == 3

    # Create immutable summary
    frozen = manager.create_frozen_block_summary(pending)
    assert frozen["immutable"] is True
    assert frozen["level"] == 0
    assert "User Q1" in frozen["summary"]


def test_hierarchical_merging():
    merger = HierarchicalMemoryMerger(blocks_per_merge=3)
    frozen_blocks = [
        {"block_id": i, "level": 0, "start_turn": (i-1)*6+1, "end_turn": i*6, "summary": f"Summary {i}"}
        for i in range(1, 5)
    ]
    merged_blocks = []

    res = merger.check_and_merge(frozen_blocks, merged_blocks)
    # Merged 3 blocks, left 1
    assert len(res["frozen_blocks"]) == 1
    assert len(res["merged_blocks"]) == 1
    assert res["merged_blocks"][0]["level"] == 1
    assert res["merged_blocks"][0]["source_block_ids"] == [1, 2, 3]


def test_memory_budget_enforcement():
    budget_mgr = MemoryBudgetManager(max_memory_tokens=300)
    raw_turns = [{"role": "user", "content": f"User question long turn {i} with many words in the sentence"} for i in range(10)]
    frozen = [{"block_id": 1, "summary": "Large frozen summary block containing detailed factual text " * 10}]
    exemplars = [{"question": "What is the fee question text " * 5, "answer": "The fee answer text " * 5} for _ in range(5)]

    safe_raw, safe_frozen, safe_merged, safe_ex = budget_mgr.enforce_budget(
        current_question="What is the hostel fee?",
        recent_raw_turns=raw_turns,
        frozen_blocks=frozen,
        merged_blocks=[],
        exemplars=exemplars,
        static_tokens=150
    )

    # Exemplars dropped first under tight token pressure
    assert len(safe_ex) < len(exemplars)
    assert len(safe_raw) >= 1  # Recent raw turn never completely dropped

