from typing import List, Dict, Any, Tuple
from backend.app.config import settings


class MemoryBudgetManager:
    """
    Enforces the strict token budget on prompt construction.
    Priority hierarchy (highest to lowest):
      1. Current user question (Never dropped)
      2. Recent raw turns
      3. Active block / pending turns
      4. Recent frozen blocks
      5. Hierarchical summaries
      6. Retrieved exemplars (Dropped first if budget is tight)
    """

    def __init__(self, max_memory_tokens: int = settings.MAX_MEMORY_TOKENS):
        self.max_memory_tokens = max_memory_tokens

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()) * 4 // 3)

    def enforce_budget(
        self,
        current_question: str,
        recent_raw_turns: List[Dict[str, str]],
        frozen_blocks: List[Dict[str, Any]],
        merged_blocks: List[Dict[str, Any]],
        exemplars: List[Dict[str, Any]],
        static_tokens: int = 1200
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Trims lower-priority context if prompt token estimate exceeds max_memory_tokens.
        Returns: (safe_raw_turns, safe_frozen_blocks, safe_merged_blocks, safe_exemplars)
        """
        # Question is untouchable
        q_tokens = self.estimate_tokens(current_question)
        available_tokens = self.max_memory_tokens - static_tokens - q_tokens

        if available_tokens <= 0:
            # Under extreme constraint, only keep question and minimal raw turn
            return recent_raw_turns[-1:] if recent_raw_turns else [], [], [], []

        safe_exemplars = list(exemplars)
        safe_merged = list(merged_blocks)
        safe_frozen = list(frozen_blocks)
        safe_raw = list(recent_raw_turns)

        # Helper to calculate dynamic memory tokens
        def total_dynamic_tokens():
            t = 0
            for ex in safe_exemplars:
                t += self.estimate_tokens(ex.get("question", "") + " " + ex.get("answer", ""))
            for m in safe_merged:
                t += self.estimate_tokens(m.get("summary", ""))
            for f in safe_frozen:
                t += self.estimate_tokens(f.get("summary", ""))
            for r in safe_raw:
                if "user" in r and "assistant" in r:
                    t += self.estimate_tokens(r["user"]) + self.estimate_tokens(r["assistant"])
                else:
                    t += self.estimate_tokens(r.get("content", ""))
            return t


        # Trim priority 6: Exemplars first
        while total_dynamic_tokens() > available_tokens and safe_exemplars:
            safe_exemplars.pop()

        # Trim priority 5: Oldest merged blocks
        while total_dynamic_tokens() > available_tokens and safe_merged:
            safe_merged.pop(0)

        # Trim priority 4: Oldest frozen blocks
        while total_dynamic_tokens() > available_tokens and safe_frozen:
            safe_frozen.pop(0)

        # Trim priority 2: Oldest raw turns (keeping at least the most recent turn)
        while total_dynamic_tokens() > available_tokens and len(safe_raw) > 1:
            safe_raw.pop(0)

        return safe_raw, safe_frozen, safe_merged, safe_exemplars
