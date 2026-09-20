import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.storage.sqlite_store import SQLiteStore
from backend.app.providers.factory import get_llm_provider
from backend.app.context.builder import ContextBuilder
from backend.app.cache.local_cache import LocalSemanticCache
from backend.app.exemplars.store import ExemplarStore
from backend.app.memory.compaction_queue import LocalCompactionQueue
from backend.app.gateway import KifayatGateway

from backend.app.api.chat import router as chat_router
from backend.app.api.feedback import router as feedback_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.cache_admin import router as cache_router
from backend.app.api.exemplars_admin import router as exemplars_router
from backend.app.api.analytics import router as analytics_router
from backend.app.api.v1_proxy import v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("kifayat.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Kifayat Intelligent LLM Context Gateway...")

    # 1. Initialize persistent SQLite store
    store = SQLiteStore(db_path=settings.SQLITE_DB_PATH)
    app.state.store = store

    # 2. Context Builder & Canonical Handbook
    context_builder = ContextBuilder(handbook_path=settings.HANDBOOK_PATH)
    app.state.context_builder = context_builder

    # 3. Provider Abstraction
    provider = get_llm_provider(handbook_text=context_builder.canonical_handbook)
    app.state.provider = provider
    logger.info(f"Active LLM Provider: {provider.provider_name}")

    # 4. Semantic Cache
    semantic_cache = LocalSemanticCache(db_path=settings.SQLITE_DB_PATH)
    app.state.semantic_cache = semantic_cache

    # 5. Exemplar Store
    exemplar_store = ExemplarStore(storage=store, provider=provider)
    await exemplar_store.seed_defaults(seed_file=settings.SEED_EXEMPLARS_PATH)
    app.state.exemplar_store = exemplar_store

    # 6. Compaction Queue
    compaction_queue = LocalCompactionQueue(session_store=store)
    compaction_queue.start()
    app.state.compaction_queue = compaction_queue

    # 7. Gateway Orchestrator
    gateway = KifayatGateway(
        store=store,
        provider=provider,
        context_builder=context_builder,
        semantic_cache=semantic_cache,
        exemplar_store=exemplar_store,
        compaction_queue=compaction_queue
    )
    app.state.gateway = gateway
    logger.info("Kifayat Gateway initialization complete.")

    yield

    logger.info("Shutting down background workers...")
    await compaction_queue.stop()


app = FastAPI(
    title="Kifayat Context Gateway",
    version="1.0.0",
    description="Intelligent LLM Context Optimization Gateway & College Helpdesk",
    lifespan=lifespan
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(chat_router)
app.include_router(feedback_router)
app.include_router(dashboard_router)
app.include_router(cache_router)
app.include_router(exemplars_router)
app.include_router(analytics_router)
app.include_router(v1_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "app_id": settings.APP_ID,
        "provider": settings.LLM_PROVIDER,
        "handbook": settings.HANDBOOK_NAME,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def root_health():
    provider = getattr(app.state, "provider", None)
    provider_name = getattr(provider, "provider_name", settings.LLM_PROVIDER)
    is_configured = bool(settings.NVIDIA_API_KEY) if provider_name == "nvidia" else True
    
    last_stat = getattr(provider, "last_status", "ready")
    if not is_configured:
        health_state = "Not Configured"
    elif last_stat == "healthy":
        health_state = "Connected"
    elif last_stat in ["error", "unreachable", "degraded"]:
        health_state = "Error"
    else:
        health_state = "Connecting"

    return {
        "status": "ok",
        "provider": provider_name,
        "status_state": health_state,
        "configured": is_configured,
        "app_id": settings.APP_ID,
        "version": settings.HANDBOOK_VERSION
    }


@app.get("/v1/provider/status")
async def provider_status():
    provider = getattr(app.state, "provider", None)
    provider_name = getattr(provider, "provider_name", settings.LLM_PROVIDER)
    is_configured = bool(settings.NVIDIA_API_KEY) if provider_name == "nvidia" else True

    last_stat = getattr(provider, "last_status", "initialized")
    if not is_configured:
        status_state = "Not Configured"
    elif last_stat == "healthy":
        status_state = "Connected"
    elif last_stat in ["error", "unreachable", "degraded"]:
        status_state = "Error"
    else:
        status_state = "Connecting"

    return {
        "provider": provider_name,
        "configured": is_configured,
        "status_state": status_state,
        "cheap_model": settings.CHEAP_MODEL_ID,
        "strong_model": settings.STRONG_MODEL_ID,
        "judge_model": settings.JUDGE_MODEL_ID,
        "supports_caching": getattr(provider, "supports_prompt_caching", False),
        "last_status": last_stat,
        "last_latency_ms": getattr(provider, "last_latency_ms", None),
        "fallback_count": getattr(provider, "fallback_count", 0),
        "api_endpoint": "https://integrate.api.nvidia.com/v1" if provider_name == "nvidia" else "local",
        "timestamp": int(time.time())
    }


@app.post("/v1/provider/test")
async def test_provider_endpoint():
    provider = getattr(app.state, "provider", None)
    if not provider:
        return {"status": "error", "status_state": "Error", "connected": False, "message": "Provider not initialized"}

    if hasattr(provider, "test_connection"):
        res = await provider.test_connection()
        # Map raw status to user-facing state: Connected, Connecting, Not Configured, Error
        raw_stat = res.get("status", "")
        if raw_stat == "healthy":
            res["status_state"] = "Connected"
        elif raw_stat == "unconfigured":
            res["status_state"] = "Not Configured"
        elif raw_stat in ["error", "unreachable"]:
            res["status_state"] = "Error"
        else:
            res["status_state"] = "Connecting"
        res["timestamp"] = int(time.time())
        return res

    import time
    start = time.perf_counter()
    try:
        res = await provider.generate(
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5
        )
        latency = round((time.perf_counter() - start) * 1000.0, 2)
        return {
            "status": "healthy",
            "status_state": "Connected",
            "connected": True,
            "provider": provider.provider_name,
            "latency_ms": latency,
            "fallback_used": getattr(res, "fallback_used", False),
            "timestamp": int(time.time()),
            "message": f"Provider {provider.provider_name} live probe successful."
        }
    except Exception as e:
        return {
            "status": "error",
            "status_state": "Error",
            "connected": False,
            "provider": getattr(provider, "provider_name", "unknown"),
            "error": str(e),
            "timestamp": int(time.time())
        }


from pydantic import BaseModel
from typing import Optional


class ProviderConfigPayload(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    provider: Optional[str] = None


@app.post("/v1/provider/configure")
async def configure_provider(payload: ProviderConfigPayload):
    from backend.app.core.security import sanitize_and_validate_api_key, is_safe_external_url, mask_api_key
    provider = getattr(app.state, "provider", None)

    # Validate API key if provided
    masked_key = None
    if payload.api_key is not None:
        raw_key = payload.api_key.strip()
        if raw_key:
            sanitized_key = sanitize_and_validate_api_key(raw_key)
            if not sanitized_key:
                return {"status": "error", "message": "Invalid API key format. Must be alphanumeric 16-128 chars."}
            settings.NVIDIA_API_KEY = sanitized_key
            if hasattr(provider, "api_key"):
                provider.api_key = sanitized_key
            masked_key = mask_api_key(sanitized_key)
        else:
            settings.NVIDIA_API_KEY = ""
            if hasattr(provider, "api_key"):
                provider.api_key = ""
            masked_key = "None"

    # Validate Base URL if provided
    if payload.base_url:
        clean_url = payload.base_url.strip()
        if not is_safe_external_url(clean_url):
            return {"status": "error", "message": "Invalid or unsafe Base URL. Must be external HTTPS."}
        settings.NVIDIA_BASE_URL = clean_url
        if hasattr(provider, "base_url"):
            provider.base_url = clean_url

    # Model update
    if payload.model:
        clean_model = payload.model.strip()
        settings.NVIDIA_MODEL = clean_model
        settings.CHEAP_MODEL_ID = clean_model
        if hasattr(provider, "default_model"):
            provider.default_model = clean_model

    return {
        "status": "success",
        "message": "Provider configuration updated successfully.",
        "provider": getattr(provider, "provider_name", settings.LLM_PROVIDER),
        "configured": bool(settings.NVIDIA_API_KEY),
        "masked_key": masked_key or mask_api_key(settings.NVIDIA_API_KEY),
        "model": getattr(provider, "default_model", settings.CHEAP_MODEL_ID),
        "base_url": getattr(provider, "base_url", settings.NVIDIA_BASE_URL)
    }


# Mount frontend static directory if exists
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
if os.path.exists(frontend_dir):
    @app.get("/", response_class=HTMLResponse)
    async def serve_index():
        index_file = os.path.join(frontend_dir, "index.html")
        with open(index_file, "r", encoding="utf-8") as f:
            content = f.read()
        resp = HTMLResponse(content=content)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp

    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

