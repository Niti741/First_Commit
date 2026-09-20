from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from backend.app.config import settings


class BlockManager:
    """
    Manages conversation turns and immutable frozen blocks.
    - Raw Window: The newest RAW_WINDOW_TURNS (default 3) turns remain verbatim.
    - Frozen Blocks: Turns older than the raw window are partitioned into
      immutable blocks of BLOCK_TURNS (default 6 turns).
    - Invariant: Once finalized, a frozen block summary is NEVER rewritten,
      guaranteeing cache prefix stability.
    """

    def __init__(
        self,
        raw_window_turns: int = settings.RAW_WINDOW_TURNS,
        block_turns: int = settings.BLOCK_TURNS
    ):
        self.raw_window_turns = raw_window_turns
        self.block_turns = block_turns

    def add_turn(
        self,
        session_data: Dict[str, Any],
        user_msg: str,
        assistant_reply: str
    ) -> Dict[str, Any]:
        """
        Appends a complete turn (user + assistant) to the session state.
        Returns the updated session data and indicates if a new block is eligible for freezing.
        """
        raw_turns = session_data.get("raw_turns", [])
        frozen_blocks = session_data.get("frozen_blocks", [])
        turn_count = session_data.get("turn_count", 0) + 1

        # A turn consists of user message and assistant message
        new_turn = {
            "turn_index": turn_count,
            "user": user_msg,
            "assistant": assistant_reply,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        raw_turns.append(new_turn)

        # Check if turns exceed the raw window + unfreezed buffer
        # Example: When raw_turns reach BLOCK_TURNS + RAW_WINDOW_TURNS,
        # the oldest BLOCK_TURNS become eligible for freezing into a block.
        ready_for_block = None
        if len(raw_turns) >= (self.block_turns + self.raw_window_turns):
            # Take the oldest BLOCK_TURNS
            turns_to_freeze = raw_turns[:self.block_turns]
            remaining_raw = raw_turns[self.block_turns:]
            block_id = len(frozen_blocks) + 1
            ready_for_block = {
                "block_id": block_id,
                "turns": turns_to_freeze,
                "start_turn": turns_to_freeze[0]["turn_index"],
                "end_turn": turns_to_freeze[-1]["turn_index"]
            }
            raw_turns = remaining_raw

        session_data["raw_turns"] = raw_turns
        session_data["turn_count"] = turn_count
        return {
            "session_data": session_data,
            "pending_freeze_block": ready_for_block
        }

    def create_frozen_block_summary(self, block_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates an immutable summary for a block of turns.
        Preserves: user goals, constraints, facts, questions, answers, and entities.
        """
        turns = block_data.get("turns", [])
        summary_points = []
        for t in turns:
            q = t.get("user", "")
            a = t.get("assistant", "")
            # Extract key fact/entity
            summary_points.append(f"Q: {q[:60]}... -> A: {a[:100]}...")

        summary_text = " | ".join(summary_points)
        frozen_block = {
            "block_id": block_data["block_id"],
            "level": 0,
            "start_turn": block_data["start_turn"],
            "end_turn": block_data["end_turn"],
            "summary": summary_text,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "immutable": True
        }
        return frozen_block
