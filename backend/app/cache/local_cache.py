import re
import sqlite3
import json
import uuid
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import numpy as np

from backend.app.cache.base import SemanticCache
from backend.app.config import settings


class LocalSemanticCache(SemanticCache):
    """
    Local Semantic Cache using SQLite persistence and NumPy cosine similarity.
    Does NOT require Redis or Valkey for local execution.
    Features:
    - Cosine vector similarity search
    - Namespace isolation (App ID, Handbook version, Language)
    - TTL expiration support
    - Safety and context hash validation
    - Invalidation by namespace
    """

    def __init__(self, db_path: str = settings.SQLITE_DB_PATH):
        self.db_path = db_path
        self._cache_hits = 0
        self._cache_misses = 0
        self._init_db()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_cache (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                hit_count INTEGER NOT NULL DEFAULT 0,
                context_hash TEXT NOT NULL,
                ttl INTEGER NOT NULL
            )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ns ON semantic_cache(namespace)")
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:

        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    async def get_similar(
        self,
        question: str,
        embedding: List[float],
        namespace: str,
        threshold: float = settings.SEMANTIC_CACHE_THRESHOLD
    ) -> Optional[Dict[str, Any]]:
        now_ts = int(time.time())
        query_vec = np.array(embedding, dtype=np.float32)
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            self._cache_misses += 1
            return None

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, question, answer, embedding, created_at, hit_count, context_hash, ttl FROM semantic_cache WHERE namespace = ?",
                (namespace,)
            )
            rows = cursor.fetchall()

        if not rows:
            self._cache_misses += 1
            return None

        best_match = None
        highest_sim = -1.0

        for row in rows:
            # Check TTL
            created_dt = datetime.fromisoformat(row["created_at"])
            created_ts = int(created_dt.timestamp())
            if (now_ts - created_ts) > row["ttl"]:
                continue

            try:
                cand_vec = np.array(json.loads(row["embedding"]), dtype=np.float32)
                cand_norm = np.linalg.norm(cand_vec)
                if cand_norm == 0:
                    continue
                # Cosine similarity
                sim = float(np.dot(query_vec, cand_vec) / (q_norm * cand_norm))
                
                # Lexical overlap verification: ensure questions share key non-stopword tokens
                q_tokens = set(re.findall(r"\w{3,}", question.lower()))
                cand_tokens = set(re.findall(r"\w{3,}", row["question"].lower()))
                stop_set = {"what", "how", "why", "when", "where", "the", "are", "and", "for", "with", "about", "tell", "kya", "hai", "kitna"}
                q_key = q_tokens - stop_set
                cand_key = cand_tokens - stop_set
                overlap = len(q_key & cand_key) / max(len(q_key | cand_key), 1) if (q_key or cand_key) else 0.0

                if sim > highest_sim and overlap >= 0.4:
                    highest_sim = sim
                    best_match = row
            except Exception:
                continue

        if best_match and highest_sim >= threshold:
            self._cache_hits += 1
            # Update hit count and last_used_at
            now_iso = datetime.now(timezone.utc).isoformat()
            new_count = best_match["hit_count"] + 1
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_cache SET hit_count = ?, last_used_at = ? WHERE id = ?",
                    (new_count, now_iso, best_match["id"])
                )
                conn.commit()

            return {
                "id": best_match["id"],
                "question": best_match["question"],
                "answer": best_match["answer"],
                "similarity": round(highest_sim, 4),
                "context_hash": best_match["context_hash"],
                "hit_count": new_count
            }

        self._cache_misses += 1
        return None

    async def set(
        self,
        question: str,
        answer: str,
        embedding: List[float],
        namespace: str,
        context_hash: str,
        ttl: int = settings.SEMANTIC_CACHE_TTL
    ) -> str:
        cache_id = f"cache-{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        emb_json = json.dumps(embedding)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Prune if max entries exceeded
            cursor.execute("SELECT COUNT(*) as count FROM semantic_cache WHERE namespace = ?", (namespace,))
            count = cursor.fetchone()["count"]
            if count >= settings.SEMANTIC_CACHE_MAX_ENTRIES:
                cursor.execute(
                    "DELETE FROM semantic_cache WHERE id IN (SELECT id FROM semantic_cache WHERE namespace = ? ORDER BY last_used_at ASC LIMIT 100)",
                    (namespace,)
                )

            cursor.execute("""
            INSERT INTO semantic_cache (id, namespace, question, answer, embedding, created_at, last_used_at, hit_count, context_hash, ttl)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """, (cache_id, namespace, question, answer, emb_json, now_iso, now_iso, context_hash, ttl))
            conn.commit()

        return cache_id

    async def delete(self, cache_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM semantic_cache WHERE id = ?", (cache_id,))
            conn.commit()

    async def invalidate(self, namespace: Optional[str] = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if namespace:
                cursor.execute("DELETE FROM semantic_cache WHERE namespace = ?", (namespace,))
            else:
                cursor.execute("DELETE FROM semantic_cache")
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    async def clear(self) -> None:
        await self.invalidate(None)

    async def stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total, SUM(hit_count) as total_hits FROM semantic_cache")
            row = cursor.fetchone()
            total_entries = row["total"] or 0
            lifetime_hits = row["total_hits"] or 0

        total_queries = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_queries) if total_queries > 0 else 0.0

        return {
            "entries_stored": total_entries,
            "session_hits": self._cache_hits,
            "session_misses": self._cache_misses,
            "session_hit_rate": round(hit_rate, 4),
            "lifetime_hits": lifetime_hits,
            "threshold": settings.SEMANTIC_CACHE_THRESHOLD,
            "ttl_seconds": settings.SEMANTIC_CACHE_TTL
        }
