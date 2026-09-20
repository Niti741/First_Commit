from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Query, HTTPException

router = APIRouter()


@router.get("/api/analytics/summary")
async def get_analytics_summary(request: Request):
    """
    Comprehensive gateway operational and token-savings summary.
    Includes actual vs estimated breakdown.
    """
    store = request.app.state.store
    summary = store.get_metrics_summary()
    mem_stats = store.get_memory_analytics()
    comp_queue = request.app.state.gateway.compaction_queue
    comp_stats = comp_queue.get_metrics()

    total_reqs = summary.get("total_requests", 0) or 0
    cache_hits = summary.get("cache_hits", 0) or 0
    cache_misses = summary.get("cache_misses", 0) or 0
    tokens_saved = summary.get("total_tokens_saved", 0) or 0
    tokens_actual = summary.get("tokens_saved_actual", 0) or 0
    tokens_est = summary.get("tokens_saved_estimated", 0) or 0
    tokens_used = summary.get("total_tokens_used", 0) or 0
    cost_saved = summary.get("total_cost_saved_usd", 0.0) or 0.0
    avoided_calls = summary.get("total_llm_calls_avoided", 0) or 0

    return {
        "total_requests": total_reqs,
        "total_conversations": summary.get("total_conversations", 0) or 0,
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
        "cache_hit_rate": round(summary.get("cache_hit_rate", 0.0), 4),
        "total_tokens_used": tokens_used,
        "total_tokens_saved": tokens_saved,
        "tokens_saved_actual": tokens_actual,
        "tokens_saved_estimated": tokens_est,
        "token_savings_pct": round((tokens_saved / (tokens_used + tokens_saved) * 100.0), 2) if (tokens_used + tokens_saved) > 0 else 0.0,
        "llm_calls_avoided": avoided_calls,
        "total_cost_saved_usd": round(cost_saved, 4),
        "context_reduction_pct": mem_stats.get("context_reduction_pct", 0.0),
        "average_latency_ms": round(summary.get("average_latency_ms", 0.0) or 0.0, 1),
        "repair_distribution": {
            "cache_hit": cache_hits,
            "rung_1_cheap": summary.get("cheap_model_calls", 0) or 0,
            "rung_2_rescue": summary.get("rung2_rescues", 0) or 0,
            "rung_3_strong": summary.get("strong_model_calls", 0) or 0
        },
        "model_usage": {
            "cheap_model_calls": summary.get("cheap_model_calls", 0) or 0,
            "strong_model_calls": summary.get("strong_model_calls", 0) or 0,
            "judge_calls": total_reqs - cache_hits,
            "embedding_calls": total_reqs
        },
        "compaction": {
            "triggered": comp_stats.get("compactions_triggered", 0),
            "queued": comp_stats.get("compactions_queued", 0),
            "completed": comp_stats.get("compactions_completed", 0),
            "failed": comp_stats.get("compactions_failed", 0),
            "average_latency_ms": comp_stats.get("average_compaction_latency_ms", 0.0)
        }
    }


@router.get("/api/analytics/requests")
async def get_analytics_requests(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    filter_type: Optional[str] = Query(None, description="cache_hit, cache_miss, rung_1, rung_2, rung_3, failed"),
    search_id: Optional[str] = Query(None)
):
    """Filterable request logs with execution metadata."""
    store = request.app.state.store
    return store.get_filtered_logs(limit=limit, filter_type=filter_type, search_id=search_id)


@router.get("/api/analytics/request/{request_id}")
async def get_analytics_request_detail(request: Request, request_id: str):
    """Detailed micro-timeline and node states for an individual request."""
    store = request.app.state.store
    log_item = store.get_request_log(request_id)
    if not log_item:
        raise HTTPException(status_code=404, detail=f"Request {request_id} not found")
    return log_item


@router.get("/api/analytics/token-savings")
async def get_token_savings_series(
    request: Request,
    limit: int = Query(50, ge=5, le=100)
):
    """Time-series data for Tokens Used vs Tokens Saved graph."""
    store = request.app.state.store
    series = store.get_token_savings_series(limit=limit)
    return {"series": series}


@router.get("/api/analytics/cache")
async def get_cache_analytics(request: Request):
    """Semantic Cache telemetry: lookups, hits, misses, lookup latency, avoided calls."""
    store = request.app.state.store
    return store.get_cache_analytics()


@router.get("/api/analytics/memory")
async def get_memory_analytics(request: Request):
    """Hierarchical memory and frozen block token breakdown."""
    store = request.app.state.store
    return store.get_memory_analytics()


@router.get("/api/analytics/exemplars")
async def get_exemplar_analytics(request: Request):
    """Exemplar win-rate statistics, top performing exemplars, and pruning candidates."""
    store = request.app.state.store
    return store.get_exemplar_analytics()


@router.get("/api/analytics/compaction")
async def get_compaction_analytics(request: Request):
    """Asynchronous compaction queue telemetry and recent execution events."""
    comp_queue = request.app.state.gateway.compaction_queue
    return comp_queue.get_metrics()
