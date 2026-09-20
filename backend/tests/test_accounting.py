import pytest
from backend.app.pricing.accounting import TokenAccountingService


def test_token_accounting_cache_hit():
    result = TokenAccountingService.account(
        model_id="semantic_cache",
        actual_input_tokens=0,
        actual_output_tokens=60,
        cache_hit=True,
        uncompressed_context_tokens=1500,
        estimated_output_tokens=60
    )
    assert result["actual_input_tokens"] == 0
    assert result["actual_output_tokens"] == 0
    assert result["llm_calls_avoided"] == 1
    assert result["actual_cost_usd"] == 0.0
    assert result["tokens_saved_estimated"] >= 1500
    assert result["is_estimated"] is True
    assert result["saving_pct"] == 100.0


def test_token_accounting_llm_execution():
    result = TokenAccountingService.account(
        model_id="meta/llama-3.2-11b-vision-instruct",
        actual_input_tokens=800,
        actual_output_tokens=150,
        cache_hit=False,
        cache_read_tokens=400,
        uncompressed_context_tokens=1600,
        is_strong_model=False
    )
    assert result["actual_input_tokens"] == 800
    assert result["actual_output_tokens"] == 150
    assert result["tokens_saved_actual"] == 400
    assert result["llm_calls_avoided"] == 0
    assert result["actual_cost_usd"] > 0.0
    assert result["baseline_cost_usd"] > result["actual_cost_usd"]
    assert result["cost_saved_usd"] > 0.0
