import asyncio
import json
import os
import sys
import time
from typing import Dict, List, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.config import settings
from backend.app.storage.sqlite_store import SQLiteStore
from backend.app.providers.factory import get_llm_provider
from backend.app.context.builder import ContextBuilder
from backend.app.cache.local_cache import LocalSemanticCache
from backend.app.exemplars.store import ExemplarStore
from backend.app.memory.compaction_queue import LocalCompactionQueue
from backend.app.gateway import KifayatGateway


async def run_evaluation(dataset_path: str = "eval/dataset.json") -> Dict[str, Any]:
    print("=" * 70)
    print("KIFAYAT GATEWAY BENCHMARK EVALUATION HARNESS")
    print("=" * 70)

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    # Initialize gateway stack
    store = SQLiteStore(db_path="backend/eval_test.db")
    context_builder = ContextBuilder(handbook_path=settings.HANDBOOK_PATH)
    provider = get_llm_provider(handbook_text=context_builder.canonical_handbook)
    semantic_cache = LocalSemanticCache(db_path="backend/eval_test.db")
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    await exemplar_store.seed_defaults()
    compaction_queue = LocalCompactionQueue(session_store=store)
    compaction_queue.start()

    gateway = KifayatGateway(
        store=store,
        provider=provider,
        context_builder=context_builder,
        semantic_cache=semantic_cache,
        exemplar_store=exemplar_store,
        compaction_queue=compaction_queue
    )

    modes = ["baseline", "naive", "cache_only", "kifayat"]
    results = {mode: {
        "total_requests": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "cache_hits": 0,
        "strong_model_calls": 0,
        "total_latency_ms": 0.0
    } for mode in modes}

    conversations = dataset.get("conversations", [])

    for mode in modes:
        print(f"\nEvaluating Mode: {mode.upper()}...")
        # Clear cache between mode runs to ensure fair benchmark
        await semantic_cache.clear()

        for conv in conversations:
            sess_id = f"eval-{mode}-{conv['id']}"
            for question in conv["turns"]:
                resp = await gateway.process_chat(
                    question=question,
                    session_id=sess_id,
                    mode=mode
                )
                receipt = resp["receipt"]
                res_bucket = results[mode]
                res_bucket["total_requests"] += 1
                res_bucket["total_tokens"] += (receipt.input_tokens + receipt.output_tokens)
                res_bucket["total_cost"] += receipt.cost_usd
                res_bucket["total_latency_ms"] += receipt.latency_ms
                if receipt.cache_hit:
                    res_bucket["cache_hits"] += 1
                if receipt.rung == 3:
                    res_bucket["strong_model_calls"] += 1

    await compaction_queue.stop()

    # Print summary table
    print("\n" + "=" * 70)
    print(f"{'Mode':<12} | {'Tokens':<10} | {'Cost (USD)':<12} | {'Cache Hits':<11} | {'Strong LLM':<10} | {'Savings %':<10}")
    print("-" * 70)

    baseline_cost = results["baseline"]["total_cost"]

    for mode in modes:
        data = results[mode]
        cost = data["total_cost"]
        savings_pct = (((baseline_cost - cost) / baseline_cost) * 100.0) if baseline_cost > 0 else 0.0
        print(
            f"{mode:<12} | "
            f"{data['total_tokens']:<10} | "
            f"${cost:<11.6f} | "
            f"{data['cache_hits']:<11} | "
            f"{data['strong_model_calls']:<10} | "
            f"{savings_pct:<10.1f}%"
        )
    print("=" * 70)
    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())
