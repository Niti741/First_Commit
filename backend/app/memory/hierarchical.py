from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone
from backend.app.config import settings


class HierarchicalMemoryMerger:
    """
    Prevents conversations with dozens of frozen blocks from exceeding token budgets.
    Architecture:
      Raw Turns -> Level 0 Frozen Blocks -> Level 1 Mid-Level Summaries -> Level 2 High-Level Overview
    All blocks remain historically traceable with immutable source_block_ids.
    """

    def __init__(self, blocks_per_merge: int = settings.BLOCKS_PER_MERGE):
        self.blocks_per_merge = blocks_per_merge

    def check_and_merge(
        self,
        frozen_blocks: List[Dict[str, Any]],
        merged_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        If there are at least `blocks_per_merge` Level 0 blocks,
        compact the oldest group into a Level 1 overview.
        If there are multiple Level 1 summaries, condenses the oldest into Level 2.
        Does not touch the newest blocks to preserve fine-grained recent context.
        """
        if len(frozen_blocks) < self.blocks_per_merge:
            return {
                "frozen_blocks": frozen_blocks,
                "merged_blocks": merged_blocks,
                "merged_count": 0,
                "tokens_saved": 0
            }

        # Take the oldest blocks_per_merge blocks
        blocks_to_merge = frozen_blocks[:self.blocks_per_merge]
        remaining_frozen = frozen_blocks[self.blocks_per_merge:]

        start_turn = blocks_to_merge[0].get("start_turn", 1)
        end_turn = blocks_to_merge[-1].get("end_turn", start_turn + 5)
        merged_id = len(merged_blocks) + 1

        summaries = [b.get("summary", "") for b in blocks_to_merge]
        raw_combined = " ".join(summaries)
        tokens_before = sum(len(s.split()) for s in summaries)

        # Create consolidated Level 1 Mid-Level Summary
        level_1_summary = (
            f"Consolidated turns {start_turn} to {end_turn}: "
            f"{raw_combined[:350]}..."
        )
        tokens_after = len(level_1_summary.split())
        tokens_saved = max(0, tokens_before - tokens_after)

        merged_block = {
            "merged_id": f"m1-{merged_id}",
            "level": 1,
            "title": f"Mid-Level Summary (Turns {start_turn}–{end_turn})",
            "start_turn": start_turn,
            "end_turn": end_turn,
            "summary": level_1_summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_block_ids": [b.get("block_id") for b in blocks_to_merge]
        }

        updated_merged = list(merged_blocks)
        updated_merged.append(merged_block)

        # Check for Level 2 Overview if we have multiple Level 1 blocks
        level_1_items = [b for b in updated_merged if b.get("level") == 1]
        if len(level_1_items) >= 4:
            # Consolidate oldest 3 Level 1 items into Level 2 High-Level Overview
            to_l2 = level_1_items[:3]
            remaining_l1 = [b for b in updated_merged if b not in to_l2]
            l2_start = to_l2[0].get("start_turn", 1)
            l2_end = to_l2[-1].get("end_turn", 50)
            l2_id = f"m2-{len(updated_merged) + 1}"
            l2_summary = (
                f"Early Conversation High-Level Overview (Turns {l2_start}–{l2_end}): "
                f"{' '.join(b.get('summary', '') for b in to_l2)[:450]}..."
            )
            l2_block = {
                "merged_id": l2_id,
                "level": 2,
                "title": f"Early Conversation Overview (Turns {l2_start}–{l2_end})",
                "start_turn": l2_start,
                "end_turn": l2_end,
                "summary": l2_summary,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_block_ids": [b.get("merged_id") for b in to_l2]
            }
            updated_merged = [l2_block] + remaining_l1

        return {
            "frozen_blocks": remaining_frozen,
            "merged_blocks": updated_merged,
            "merged_count": 1,
            "tokens_saved": tokens_saved
        }
