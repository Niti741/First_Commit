import time
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.providers.nvidia_provider import NVIDIAProvider
from backend.app.providers.mock_provider import MockProvider
from backend.app.gateway import KifayatGateway

logger = logging.getLogger("kifayat.api.v1_proxy")

v1_router = APIRouter(prefix="/v1", tags=["OpenAI Reverse Proxy"])


class ChatCompletionMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "kifayat-gateway"
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 500
    stream: Optional[bool] = False
    session_id: Optional[str] = None
    mode: Optional[str] = "kifayat"


@v1_router.get("/models")
async def list_models():
    """OpenAI-compatible list models endpoint."""
    return {
        "object": "list",
        "data": [
            {
                "id": "kifayat-gateway",
                "object": "model",
                "created": 1720000000,
                "owned_by": "kifayat",
                "permission": [],
                "root": "kifayat-gateway"
            },
            {
                "id": "kifayat-optimized",
                "object": "model",
                "created": 1720000000,
                "owned_by": "kifayat",
                "root": "meta/llama-3.2-11b-vision-instruct"
            }
        ]
    }


@v1_router.post("/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """
    Drop-in OpenAI-compatible /v1/chat/completions endpoint.
    Supports dynamic user API key overrides via Authorization: Bearer <key>.
    """
    gateway: KifayatGateway = request.app.state.gateway
    if not gateway:
        raise HTTPException(status_code=500, detail="Kifayat Gateway not initialized")

    # 1. Extract dynamic User API Key if provided
    user_api_key = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
        if token and token != "sk-kifayat-default":
            user_api_key = token
            logger.info("🔑 Dynamic per-user API key detected. Overriding provider credential for request.")

    # 2. Extract last user question and prior turns
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    user_messages = [m for m in req.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="Must contain at least one user message")

    last_user_message = user_messages[-1].content
    session_id = req.session_id or f"sess-proxy-{uuid.uuid4().hex[:8]}"

    # If user provided a specific API key, instantiate a request-scoped provider
    active_gateway = gateway
    if user_api_key:
        from backend.app.core.security import create_scoped_gateway
        active_gateway = create_scoped_gateway(gateway, user_api_key)

    # 3. Handle Streaming vs Non-Streaming
    req_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    if req.stream:
        async def sse_generator():
            try:
                async for event in active_gateway.process_stream(
                    session_id=session_id,
                    question=last_user_message,
                    mode=req.mode or "kifayat"
                ):
                    event_type = event.get("type")
                    if event_type == "chunk":
                        content = event.get("content", "")
                        chunk_payload = {
                            "id": req_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": req.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": content},
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk_payload)}\n\n"

                    elif event_type == "receipt":
                        # Final terminal chunk with finish_reason
                        final_chunk = {
                            "id": req_id,
                            "object": "chat.completion.chunk",
                            "created": created_ts,
                            "model": req.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {},
                                    "finish_reason": "stop"
                                }
                            ],
                            "kifayat_receipt": event.get("receipt", {})
                        }
                        yield f"data: {json.dumps(final_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in OpenAI proxy stream: {e}")
                err_payload = {"error": str(e)}
                yield f"data: {json.dumps(err_payload)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    # Non-streaming execution
    res = await active_gateway.process_query(
        session_id=session_id,
        question=last_user_message,
        mode=req.mode or "kifayat"
    )

    return JSONResponse({
        "id": req_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": res.model_id or req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": res.text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": res.input_tokens,
            "completion_tokens": res.output_tokens,
            "total_tokens": res.input_tokens + res.output_tokens
        },
        "kifayat_metadata": {
            "cache_hit": res.cache_hit,
            "rung": res.rung,
            "tokens_saved": res.tokens_saved,
            "cost_usd": res.cost_usd,
            "savings_pct": res.savings_pct,
            "latency_ms": res.latency_ms
        }
    })
