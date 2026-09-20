from typing import Dict, Any, Optional
from backend.app.config import settings


class TokenAccountingService:
    """
    Central Token Accounting Service.
    Strictly distinguishes between provider-reported ACTUAL tokens and
    uncompressed/avoided ESTIMATED tokens, ensuring zero fabricated metrics.
    """

    @classmethod
    def account(
        cls,
        model_id: str,
        actual_input_tokens: int,
        actual_output_tokens: int,
        cache_hit: bool = False,
        cache_read_tokens: int = 0,
        uncompressed_context_tokens: int = 0,
        estimated_output_tokens: int = 0,
        is_strong_model: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates exact actual and estimated token accounting:
        - actual_input_tokens: Provider reported prompt tokens
        - actual_output_tokens: Provider reported completion tokens
        - estimated_avoided_input_tokens: Tokens avoided via caching, prefix sharing, or memory compaction
        - estimated_avoided_output_tokens: Tokens avoided on cache hit
        - tokens_saved_actual: Exact prompt cache read tokens reported by provider/cache
        - tokens_saved_estimated: Estimated uncompressed tokens avoided
        - actual_cost: Real dollar cost based on model rates
        - baseline_cost: Unoptimized baseline cost (strong model without caching)
        - cost_saved: Baseline minus actual cost
        """
        # Baseline context assumes uncompressed context or input tokens with strong model
        baseline_input = max(uncompressed_context_tokens, actual_input_tokens)
        baseline_output = max(actual_output_tokens, estimated_output_tokens, 50)

        # Baseline cost (strong model for all tokens, zero prompt caching)
        baseline_cost = (
            (baseline_input / 1000.0) * settings.COST_STRONG_INPUT +
            (baseline_output / 1000.0) * settings.COST_STRONG_OUTPUT
        )

        if cache_hit:
            # On cache hit, actual generation tokens = 0
            actual_in = 0
            actual_out = 0
            avoided_in = baseline_input
            avoided_out = baseline_output
            tokens_saved_actual = 0
            tokens_saved_estimated = avoided_in + avoided_out
            is_estimated = True
            actual_cost = 0.0
            llm_calls_avoided = 1
        else:
            actual_in = actual_input_tokens
            actual_out = actual_output_tokens
            avoided_in = max(0, baseline_input - actual_in)
            avoided_out = 0
            tokens_saved_actual = cache_read_tokens
            tokens_saved_estimated = avoided_in
            is_estimated = (cache_read_tokens == 0 and avoided_in > 0)
            llm_calls_avoided = 0

            # Determine rate
            if is_strong_model:
                in_rate = settings.COST_STRONG_INPUT
                out_rate = settings.COST_STRONG_OUTPUT
            else:
                in_rate = settings.COST_CHEAP_INPUT
                out_rate = settings.COST_CHEAP_OUTPUT

            uncached_in = max(0, actual_in - cache_read_tokens)
            cost_uncached = (uncached_in / 1000.0) * in_rate
            cost_cached = (cache_read_tokens / 1000.0) * settings.COST_CACHE_READ
            cost_out = (actual_out / 1000.0) * out_rate
            actual_cost = cost_uncached + cost_cached + cost_out

        cost_saved = max(0.0, baseline_cost - actual_cost)
        saving_pct = (cost_saved / baseline_cost * 100.0) if baseline_cost > 0 else 0.0

        return {
            "actual_input_tokens": actual_in,
            "actual_output_tokens": actual_out,
            "estimated_avoided_input_tokens": avoided_in,
            "estimated_avoided_output_tokens": avoided_out,
            "tokens_saved_actual": tokens_saved_actual,
            "tokens_saved_estimated": tokens_saved_estimated,
            "total_tokens_saved": tokens_saved_actual + tokens_saved_estimated,
            "is_estimated": is_estimated,
            "llm_calls_avoided": llm_calls_avoided,
            "actual_cost_usd": round(actual_cost, 6),
            "baseline_cost_usd": round(baseline_cost, 6),
            "cost_saved_usd": round(cost_saved, 6),
            "saving_pct": round(saving_pct, 2)
        }
