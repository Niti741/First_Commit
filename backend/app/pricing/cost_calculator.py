from typing import Dict, Any
from backend.app.config import settings


class CostCalculator:
    """
    Centralized pricing and token cost calculation.
    Calculates actual cost vs unoptimized baseline cost and savings percentage.
    """

    @classmethod
    def calculate(
        cls,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
        cache_hit: bool = False,
        is_strong_model: bool = False
    ) -> Dict[str, float]:
        """
        Returns {
            'actual_cost': float,
            'baseline_cost': float,
            'cost_saved': float,
            'tokens_saved': int,
            'saving_pct': float
        }
        """
        # 1. Calculate Baseline Cost (Unoptimized: Strong model for all tokens, zero prompt caching)
        # In baseline, the uncompressed prompt would have included extra historical turns
        baseline_input = input_tokens + (cache_read_tokens if cache_hit else 0)
        baseline_cost = (baseline_input / 1000.0) * settings.COST_STRONG_INPUT + \
                        (max(output_tokens, 50) / 1000.0) * settings.COST_STRONG_OUTPUT

        # 2. Calculate Actual Cost
        if cache_hit:
            # Zero LLM token generation cost on semantic cache hit
            actual_cost = 0.0
            tokens_saved = baseline_input + output_tokens
        else:
            if is_strong_model:
                in_rate = settings.COST_STRONG_INPUT
                out_rate = settings.COST_STRONG_OUTPUT
            else:
                in_rate = settings.COST_CHEAP_INPUT
                out_rate = settings.COST_CHEAP_OUTPUT

            uncached_input = max(0, input_tokens - cache_read_tokens)
            cost_uncached = (uncached_input / 1000.0) * in_rate
            cost_cached = (cache_read_tokens / 1000.0) * settings.COST_CACHE_READ
            cost_out = (output_tokens / 1000.0) * out_rate

            actual_cost = cost_uncached + cost_cached + cost_out
            tokens_saved = cache_read_tokens

        cost_saved = max(0.0, baseline_cost - actual_cost)
        saving_pct = (cost_saved / baseline_cost * 100.0) if baseline_cost > 0 else 0.0

        return {
            "actual_cost": round(actual_cost, 6),
            "baseline_cost": round(baseline_cost, 6),
            "cost_saved": round(cost_saved, 6),
            "tokens_saved": int(tokens_saved),
            "saving_pct": round(saving_pct, 2)
        }
