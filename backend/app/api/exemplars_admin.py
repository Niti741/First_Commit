import uuid
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()


class NewExemplarRequest(BaseModel):
    question: str
    answer: str
    category: str = "general"
    language: str = "en"


class UpdateStatusRequest(BaseModel):
    status: str  # 'active', 'candidate_for_pruning', 'archived'


@router.get("/api/exemplars")
async def list_exemplars(request: Request, status: Optional[str] = None):
    exemplar_store = request.app.state.exemplar_store
    return exemplar_store.storage.get_all(status=status)


@router.post("/api/exemplars")
async def create_exemplar(req: NewExemplarRequest, request: Request):
    gateway = request.app.state.gateway
    embeddings = await gateway.provider.embed([req.question])
    ex_id = f"ex-man-{uuid.uuid4().hex[:8]}"

    exemplar_data = {
        "id": ex_id,
        "question": req.question,
        "answer": req.answer,
        "category": req.category,
        "language": req.language,
        "embedding": embeddings[0],
        "times_selected": 0,
        "successful_rescues": 0,
        "failed_rescues": 0,
        "win_rate": 0.0,
        "quality_score": 0.50,
        "impact_score": 0.50,
        "status": "active"
    }
    gateway.exemplar_store.storage.add_exemplar(exemplar_data)
    return {"status": "success", "exemplar": exemplar_data}


@router.post("/api/exemplars/{exemplar_id}/status")
async def update_exemplar_status(exemplar_id: str, req: UpdateStatusRequest, request: Request):
    exemplar_store = request.app.state.exemplar_store
    exemplar_store.storage.update_status(exemplar_id, req.status)
    return {"status": "success", "id": exemplar_id, "new_status": req.status}


@router.delete("/api/exemplars/{exemplar_id}")
async def delete_exemplar(exemplar_id: str, request: Request):
    exemplar_store = request.app.state.exemplar_store
    exemplar_store.storage.delete(exemplar_id)
    return {"status": "success", "deleted": exemplar_id}
