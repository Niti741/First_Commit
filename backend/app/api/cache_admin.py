from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Request

router = APIRouter()


class InvalidateRequest(BaseModel):
    namespace: Optional[str] = None


@router.get("/api/cache/stats")
async def get_cache_stats(request: Request):
    cache = request.app.state.semantic_cache
    return await cache.stats()


@router.post("/api/cache/invalidate")
async def invalidate_cache(req: InvalidateRequest, request: Request):
    cache = request.app.state.semantic_cache
    deleted = await cache.invalidate(req.namespace)
    return {"status": "success", "deleted_entries": deleted, "namespace": req.namespace}


@router.post("/api/cache/clear")
async def clear_cache(request: Request):
    cache = request.app.state.semantic_cache
    await cache.clear()
    return {"status": "success", "message": "Semantic cache cleared completely."}
