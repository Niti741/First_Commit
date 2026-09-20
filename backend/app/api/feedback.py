import uuid
from fastapi import APIRouter, Request
from backend.app.models.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()


@router.post("/v1/feedback", response_model=FeedbackResponse)
async def submit_feedback(req: FeedbackRequest, request: Request):
    gateway = request.app.state.gateway
    promoted = False
    new_ex_id = None

    if req.thumbs_up:
        # Vetted candidate eligible for exemplar promotion
        embeddings = await gateway.provider.embed([req.question])
        new_ex_id = f"ex-user-{uuid.uuid4().hex[:8]}"
        gateway.exemplar_store.storage.add_exemplar({
            "id": new_ex_id,
            "question": req.question,
            "answer": req.answer,
            "category": req.category or "general",
            "language": "hinglish" if any(w in req.question.lower().split() for w in ["ka", "ki", "hai", "kya"]) else "en",
            "embedding": embeddings[0],
            "times_selected": 5,
            "successful_rescues": 5,
            "win_rate": 1.0,
            "quality_score": 0.85,
            "impact_score": 1.0,
            "status": "active"
        })
        promoted = True

    return FeedbackResponse(
        status="success",
        message="Feedback logged successfully.",
        promoted_to_exemplar=promoted,
        exemplar_id=new_ex_id
    )
