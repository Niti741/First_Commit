import json
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from backend.app.config import settings
from backend.app.storage.base import BaseExemplarStore
from backend.app.providers.base import LLMProvider
from backend.app.exemplars.scoring import ExemplarScorer
from backend.app.exemplars.pruning import ExemplarPruner

logger = logging.getLogger("kifayat.exemplars")


class ExemplarStore:
    def __init__(self, storage: BaseExemplarStore, provider: LLMProvider):
        self.storage = storage
        self.provider = provider

    async def seed_defaults(self, seed_file: str = settings.SEED_EXEMPLARS_PATH):
        """Seeds initial vetted exemplars if store is currently empty."""
        existing = self.storage.get_all()
        if existing:
            return

        if not os.path.exists(seed_file):
            logger.warning(f"Seed exemplars file not found at {seed_file}")
            return

        with open(seed_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        questions = [item["question"] for item in raw_data]
        embeddings = await self.provider.embed(questions)

        for item, emb in zip(raw_data, embeddings):
            item["embedding"] = emb
            item["quality_score"] = 0.85
            item["impact_score"] = 1.0
            item["times_selected"] = 10
            item["successful_rescues"] = 9
            item["win_rate"] = 0.90
            item["status"] = "active"
            self.storage.add_exemplar(item)

        logger.info(f"Seeded {len(raw_data)} exemplars into ExemplarStore.")

    async def retrieve(
        self,
        query_embedding: List[float],
        top_k: int = settings.EXEMPLAR_TOP_K,
        min_similarity: float = 0.60
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-K most semantically relevant exemplars.
        Filters out low-similarity or non-active exemplars.
        """
        all_exemplars = self.storage.get_all(status="active")
        if not all_exemplars or not query_embedding:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        scored_candidates = []
        for ex in all_exemplars:
            emb = ex.get("embedding")
            if not emb:
                continue
            cand_vec = np.array(emb, dtype=np.float32)
            c_norm = np.linalg.norm(cand_vec)
            if c_norm == 0:
                continue

            sim = float(np.dot(q_vec, cand_vec) / (q_norm * c_norm))
            if sim >= min_similarity:
                # Combined rank: similarity + quality_score bonus
                composite_score = (sim * 0.7) + (ex.get("quality_score", 0.5) * 0.3)
                scored_candidates.append((composite_score, sim, ex))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        results = []
        for composite, sim, ex in scored_candidates[:top_k]:
            ex_copy = dict(ex)
            ex_copy["similarity"] = round(sim, 4)
            results.append(ex_copy)

        return results

    def record_outcome(self, exemplar_id: str, success: bool):
        self.storage.update_stats(exemplar_id, success)
