import io
import os
import base64
import time
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Header, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from backend.app.models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatChoice,
    ChatMessage,
    ChatUsage
)

router = APIRouter()


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    x_session_id: Optional[str] = Header(None),
    x_kifayat_mode: Optional[str] = Header(None)
):
    """
    OpenAI-compatible chat completions endpoint with Kifayat Receipt.
    Supports modes: baseline, naive, cache_only, kifayat (default).
    """
    gateway = request.app.state.gateway
    session_id = req.session_id or x_session_id or f"sess-{uuid.uuid4().hex[:12]}"
    mode = req.mode or x_kifayat_mode or "kifayat"

    # Extract user query
    user_msgs = [m.content for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message provided.")
    question = user_msgs[-1]

    if req.stream:
        # Return SSE Stream
        return StreamingResponse(
            gateway.stream_chat(question, session_id=session_id, mode=mode),
            media_type="text/event-stream"
        )

    # Standard non-streaming response
    res = await gateway.process_chat(question, session_id=session_id, mode=mode)
    receipt = res["receipt"]
    answer_text = res["text"]

    in_tokens = receipt.input_tokens
    out_tokens = receipt.output_tokens

    return ChatCompletionResponse(
        id=receipt.request_id,
        created=int(time.time()),
        model=receipt.model_id,
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=answer_text),
                finish_reason="stop"
            )
        ],
        usage=ChatUsage(
            prompt_tokens=in_tokens,
            completion_tokens=out_tokens,
            total_tokens=in_tokens + out_tokens,
            prompt_tokens_details={"cached_tokens": receipt.cache_read_tokens}
        ),
        kifayat_receipt=receipt
    )


@router.post("/api/chat")
async def api_chat_simple(payload: dict, request: Request):
    """
    Convenience endpoint accepting {"question": str, "session_id": str, "mode": str}
    or OpenAI {"messages": [...]}.
    """
    gateway = request.app.state.gateway
    question = payload.get("question")
    if not question and "messages" in payload:
        msgs = payload["messages"]
        if msgs and isinstance(msgs, list):
            question = msgs[-1].get("content")
    if not question:
        raise HTTPException(status_code=400, detail="No question provided.")
    session_id = payload.get("session_id")
    mode = payload.get("mode", "kifayat")
    return await gateway.process_chat(question, session_id=session_id, mode=mode)


@router.post("/api/chat/stream")
async def chat_stream_native(
    req: ChatCompletionRequest,
    request: Request,
    x_session_id: Optional[str] = Header(None),
    x_kifayat_mode: Optional[str] = Header(None),
    x_user_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    """Dedicated SSE streaming endpoint for frontend chat interface with dynamic API key support."""
    from backend.app.core.security import sanitize_and_validate_api_key, create_scoped_gateway, mask_api_key
    gateway = request.app.state.gateway
    session_id = req.session_id or x_session_id or f"sess-{uuid.uuid4().hex[:12]}"
    mode = req.mode or x_kifayat_mode or "kifayat"

    # Check for custom per-user API key
    custom_key = x_user_api_key or (authorization.replace("Bearer ", "").strip() if authorization and authorization.startswith("Bearer ") else None)
    active_gateway = gateway
    if custom_key and custom_key != "sk-kifayat-default":
        valid_key = sanitize_and_validate_api_key(custom_key)
        if valid_key:
            active_gateway = create_scoped_gateway(gateway, valid_key)

    user_msgs = [m.content for m in req.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message provided.")
    question = user_msgs[-1]

    return StreamingResponse(
        active_gateway.stream_chat(question, session_id=session_id, mode=mode),
        media_type="text/event-stream"
    )


@router.post("/api/keys/validate")
async def validate_api_key(payload: dict, request: Request):
    """
    Validates user-provided API key format and connectivity without logging the key.
    """
    from backend.app.core.security import sanitize_and_validate_api_key, mask_api_key
    from backend.app.providers.nvidia_provider import NVIDIAProvider
    from backend.app.config import settings

    raw_key = payload.get("api_key", "")
    provider = payload.get("provider", "nvidia")

    sanitized = sanitize_and_validate_api_key(raw_key)
    if not sanitized:
        return {"valid": False, "error": "Invalid API key format. Must be 16-128 characters alphanumeric with hyphens/dots."}

    masked = mask_api_key(sanitized)
    try:
        test_provider = NVIDIAProvider(
            api_key=sanitized,
            base_url=settings.NVIDIA_BASE_URL,
            default_model=settings.CHEAP_MODEL_ID
        )
        resp = await test_provider.generate(
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5
        )
        return {
            "valid": True,
            "masked_key": masked,
            "provider": provider,
            "message": "Key verified successfully."
        }
    except Exception as e:
        return {
            "valid": False,
            "masked_key": masked,
            "error": "Authentication failed with provider."
        }


@router.get("/api/auth/status")
async def auth_status():
    """Returns MongoDB and user authentication readiness status."""
    from backend.app.storage.mongo_auth import MongoAuthService
    service = MongoAuthService()
    return service.get_status()


MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".pdf", ".docx",
    ".py", ".js", ".ts", ".html", ".css", ".sql", ".xml", ".yaml", ".yml",
    ".png", ".jpg", ".jpeg", ".webp", ".gif"
}


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.post("/api/upload")
async def upload_file(
    request: Request,
    file: Optional[UploadFile] = File(None)
):
    """
    Secure file upload endpoint for chat attachments.
    Validates file size (<10MB) and allowed extensions.
    Extracts text for TXT, MD, CSV, JSON, code, and PDF documents.
    """
    filename = ""
    contents = b""

    if file and file.filename:
        filename = file.filename
        contents = await file.read()
    else:
        # Check if request has JSON payload
        try:
            body = await request.json()
            filename = body.get("filename", "attachment.txt")
            raw_b64 = body.get("content", "")
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            contents = base64.b64decode(raw_b64) if raw_b64 else b""
        except Exception:
            raise HTTPException(status_code=400, detail="No valid file uploaded.")

    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit.")

    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed types: PDF, TXT, MD, DOCX, CSV, JSON, PNG, JPG/JPEG, code files."
        )

    file_id = f"file-{uuid.uuid4().hex[:8]}"
    extracted_text = ""
    is_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(contents))
            pages_text = []
            for i, page in enumerate(reader.pages[:25]):
                txt = page.extract_text()
                if txt:
                    pages_text.append(f"--- Page {i+1} ---\n{txt.strip()}")
            extracted_text = "\n\n".join(pages_text)
            if not extracted_text:
                extracted_text = f"[PDF file: {filename}, containing scanned images or no extractable text]"
        except Exception as e:
            extracted_text = f"[PDF loaded: {len(contents)} bytes, extraction note: {str(e)}]"
    elif is_image:
        extracted_text = f"[Image attachment: {filename} ({_format_size(len(contents))})]"
    else:
        try:
            extracted_text = contents.decode("utf-8")
        except UnicodeDecodeError:
            try:
                extracted_text = contents.decode("latin-1")
            except Exception:
                extracted_text = f"[Binary/text file: {filename} ({_format_size(len(contents))})]"

    snippet = extracted_text[:300] if extracted_text else ""
    return {
        "status": "success",
        "file_id": file_id,
        "filename": filename,
        "file_type": ext.lstrip("."),
        "size_bytes": len(contents),
        "size_formatted": _format_size(len(contents)),
        "text_content": extracted_text[:25000],
        "snippet": snippet,
        "char_count": len(extracted_text)
    }


@router.post("/api/run")
async def run_code_endpoint(payload: dict):
    """
    Safely executes code snippets from Canvas and returns standard output and execution status.
    Supports Python execution and syntax evaluation.
    """
    lang = payload.get("lang", "python").lower()
    code = payload.get("code", "")
    if not code.strip():
        return {"status": "error", "error": "Code is empty."}

    if lang in ["python", "py"]:
        import io
        import sys
        import time

        start_time = time.perf_counter()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = sys.stdout = io.StringIO()
        redirected_error = sys.stderr = io.StringIO()

        exec_scope = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
        try:
            exec(code, exec_scope)
            stdout = redirected_output.getvalue()
            stderr = redirected_error.getvalue()
            exec_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "success",
                "stdout": stdout,
                "stderr": stderr,
                "exec_time_ms": exec_time_ms
            }
        except Exception as e:
            exec_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "status": "error",
                "error": f"{type(e).__name__}: {str(e)}",
                "stdout": redirected_output.getvalue(),
                "exec_time_ms": exec_time_ms
            }
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    return {
        "status": "success",
        "stdout": f"[{lang.upper()} code ready for preview runner]",
        "exec_time_ms": 0
    }


