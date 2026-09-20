import logging
import uuid
from typing import Optional, Dict, Any, List
import numpy as np

from backend.app.providers.base import LLMProvider
from backend.app.exemplars.store import ExemplarStore

logger = logging.getLogger("kifayat.exemplars.mining")


class AutonomousExemplarMiner:
    """
    Autonomous Active-Learning Exemplar Miner.
    Captures edge-case questions answered by Rung 3 (Strong Model),
    verifies quality, checks semantic uniqueness, and registers them
    as newly mined exemplars to rescue future queries at Rung 2.
    """

    @classmethod
    async def mine_candidate(
        cls,
        question: str,
        answer: str,
        provider: LLMProvider,
        exemplar_store: ExemplarStore,
        category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        try:
            if not question or not answer:
                return None

            clean_q = question.strip()
            clean_ans = answer.strip()

            # 1. Quality Filters
            if len(clean_q) < 5 or len(clean_ans) < 25:
                return None

            # Skip canned refusals or error texts
            low_ans = clean_ans.lower()
            if any(r in low_ans for r in ["as an ai language model", "i cannot answer", "generation error"]):
                return None

            # 2. Compute semantic embedding
            embeddings = await provider.embed([clean_q])
            if not embeddings or not embeddings[0]:
                return None
            q_emb = embeddings[0]

            # 3. Deduplication Check against existing exemplars
            all_existing = exemplar_store.storage.get_all()
            q_vec = np.array(q_emb, dtype=np.float32)
            q_norm = np.linalg.norm(q_vec)

            if q_norm > 0 and all_existing:
                for ex in all_existing:
                    ex_emb = ex.get("embedding")
                    if ex_emb:
                        ex_vec = np.array(ex_emb, dtype=np.float32)
                        ex_norm = np.linalg.norm(ex_vec)
                        if ex_norm > 0:
                            similarity = float(np.dot(q_vec, ex_vec) / (q_norm * ex_norm))
                            if similarity >= 0.90:
                                logger.info(f"Query '{clean_q[:40]}...' is already represented (sim={similarity:.2f}). Skipping.")
                                return None

            # 4. Infer Category and Language
            hinglish_markers = ["ka", "ki", "ke", "hai", "kya", "kitna", "kahan", "nahi", "isme", "mein"]
            is_hinglish = any(w in clean_q.lower().split() for w in hinglish_markers)
            lang = "hinglish" if is_hinglish else "en"

            cat = category or "general"
            if any(w in clean_q.lower() for w in ["code", "function", "python", "sql", "api", "bug", "html", "css", "js"]):
                cat = "programming"
            elif any(w in clean_q.lower() for w in ["explain", "why", "how", "what is", "difference", "compare"]):
                cat = "reasoning"

            # 5. Form candidate exemplar
            exemplar_id = f"mined_{uuid.uuid4().hex[:8]}"
            new_exemplar = {
                "id": exemplar_id,
                "question": clean_q,
                "answer": clean_ans,
                "category": cat,
                "language": lang,
                "embedding": q_emb,
                "quality_score": 0.90,
                "impact_score": 1.0,
                "times_selected": 0,
                "successful_rescues": 0,
                "win_rate": 0.80,
                "status": "active"
            }

            exemplar_store.storage.add_exemplar(new_exemplar)
            logger.info(f"⚡ [Autonomous Miner] Mined new rescue exemplar #{exemplar_id}: '{clean_q[:50]}...'")
            return new_exemplar

        except Exception as e:
            logger.warning(f"Failed to mine exemplar candidate: {e}")
            return None
