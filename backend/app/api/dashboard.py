from typing import Optional
from fastapi import APIRouter, Request, Query
from backend.app.models.schemas import DashboardStats

router = APIRouter()


@router.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(request: Request):
    store = request.app.state.store
    summary = store.get_metrics_summary()
    return DashboardStats(
        total_requests=summary.get("total_requests", 0) or 0,
        total_conversations=summary.get("total_conversations", 0) or 0,
        cache_hits=summary.get("cache_hits", 0) or 0,
        cache_misses=summary.get("cache_misses", 0) or 0,
        cache_hit_rate=round(summary.get("cache_hit_rate", 0.0), 4),
        total_tokens_saved=summary.get("total_tokens_saved", 0) or 0,
        total_cost_saved_usd=round(summary.get("total_cost_saved_usd", 0.0) or 0.0, 4),
        average_latency_ms=round(summary.get("average_latency_ms", 0.0) or 0.0, 1),
        strong_model_calls=summary.get("strong_model_calls", 0) or 0,
        cheap_model_calls=summary.get("cheap_model_calls", 0) or 0,
        repair_success_rate=round(summary.get("repair_success_rate", 1.0), 4),
        actual_cost_usd=round(summary.get("actual_cost_usd", 0.0) or 0.0, 4),
        baseline_cost_usd=round(summary.get("baseline_cost_usd", 0.0) or 0.0, 4),
        savings_pct=round(summary.get("savings_pct", 0.0), 2),
        active_exemplars=summary.get("active_exemplars", 0) or 0,
        total_blocks_frozen=summary.get("total_blocks_frozen", 0) or 0,
        total_blocks_merged=summary.get("total_blocks_merged", 0) or 0
    )


@router.get("/api/dashboard/requests")
async def get_dashboard_requests(request: Request, limit: int = Query(50, ge=1, le=200)):
    store = request.app.state.store
    return store.get_recent_logs(limit=limit)


@router.get("/api/dashboard/memory")
async def get_dashboard_memory(request: Request, session_id: Optional[str] = Query(None)):

    store = request.app.state.store
    if session_id:
        sess = store.get_session(session_id)
        return sess or {"message": "Session not found"}
    sessions = store.list_sessions(limit=30)
    return {"sessions": sessions}
