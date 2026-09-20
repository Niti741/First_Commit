import sqlite3
import json
import os
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from backend.app.storage.base import SessionStore, BaseExemplarStore, RequestLogStore


class SQLiteStore(SessionStore, BaseExemplarStore, RequestLogStore):
    def __init__(self, db_path: str = "backend/kifayat.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Sessions
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    raw_turns TEXT NOT NULL,
                    frozen_blocks TEXT NOT NULL,
                    merged_blocks TEXT NOT NULL,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)

                # Exemplars
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS exemplars (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT NOT NULL,
                    language TEXT NOT NULL,
                    embedding TEXT,
                    times_selected INTEGER NOT NULL DEFAULT 0,
                    successful_rescues INTEGER NOT NULL DEFAULT 0,
                    failed_rescues INTEGER NOT NULL DEFAULT 0,
                    win_rate REAL NOT NULL DEFAULT 0.0,
                    quality_score REAL NOT NULL DEFAULT 0.0,
                    impact_score REAL NOT NULL DEFAULT 0.0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    last_used_at TEXT
                )
                """)

                # Request Logs
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS request_logs (
                    request_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    rung INTEGER NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
                    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
                    tokens_saved INTEGER NOT NULL DEFAULT 0,
                    tokens_saved_actual INTEGER NOT NULL DEFAULT 0,
                    tokens_saved_estimated INTEGER NOT NULL DEFAULT 0,
                    is_estimated_tokens INTEGER NOT NULL DEFAULT 0,
                    llm_calls_avoided INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0.0,
                    baseline_cost_usd REAL NOT NULL DEFAULT 0.0,
                    saving_pct REAL NOT NULL DEFAULT 0.0,
                    cache_hit INTEGER NOT NULL DEFAULT 0,
                    cache_type TEXT,
                    similarity REAL,
                    latency_ms REAL NOT NULL DEFAULT 0.0,
                    prefix_hash TEXT,
                    judge_score INTEGER,
                    judge_verdict TEXT,
                    execution_path TEXT,
                    node_states TEXT,
                    node_details TEXT,
                    timeline TEXT
                )
                """)

                # Run migrations for existing DBs if columns are missing
                migration_cols = [
                    ("tokens_saved_actual", "INTEGER NOT NULL DEFAULT 0"),
                    ("tokens_saved_estimated", "INTEGER NOT NULL DEFAULT 0"),
                    ("is_estimated_tokens", "INTEGER NOT NULL DEFAULT 0"),
                    ("llm_calls_avoided", "INTEGER NOT NULL DEFAULT 0"),
                    ("execution_path", "TEXT"),
                    ("node_states", "TEXT"),
                    ("node_details", "TEXT"),
                    ("timeline", "TEXT")
                ]
                for col_name, col_def in migration_cols:
                    try:
                        cursor.execute(f"ALTER TABLE request_logs ADD COLUMN {col_name} {col_def}")
                    except sqlite3.OperationalError:
                        pass

                # Semantic Cache Table
                cursor.execute("""
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
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_ns ON semantic_cache(namespace)")
                conn.commit()

    # --- SessionStore Methods ---
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return {
                    "session_id": row["session_id"],
                    "raw_turns": json.loads(row["raw_turns"]),
                    "frozen_blocks": json.loads(row["frozen_blocks"]),
                    "merged_blocks": json.loads(row["merged_blocks"]),
                    "turn_count": row["turn_count"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            raw_turns_str = json.dumps(session_data.get("raw_turns", []))
            frozen_blocks_str = json.dumps(session_data.get("frozen_blocks", []))
            merged_blocks_str = json.dumps(session_data.get("merged_blocks", []))
            turn_count = session_data.get("turn_count", len(session_data.get("raw_turns", [])))

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO sessions (session_id, raw_turns, frozen_blocks, merged_blocks, turn_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    raw_turns = excluded.raw_turns,
                    frozen_blocks = excluded.frozen_blocks,
                    merged_blocks = excluded.merged_blocks,
                    turn_count = excluded.turn_count,
                    updated_at = excluded.updated_at
                """, (session_id, raw_turns_str, frozen_blocks_str, merged_blocks_str, turn_count, now, now))
                conn.commit()

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT session_id, turn_count, created_at, updated_at FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]

    # --- BaseExemplarStore Methods ---
    def add_exemplar(self, exemplar: Dict[str, Any]) -> None:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            emb_str = json.dumps(exemplar.get("embedding")) if exemplar.get("embedding") else None
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO exemplars (
                    id, question, answer, category, language, embedding,
                    times_selected, successful_rescues, failed_rescues, win_rate,
                    quality_score, impact_score, status, created_at, last_used_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    question = excluded.question,
                    answer = excluded.answer,
                    category = excluded.category,
                    language = excluded.language,
                    embedding = COALESCE(excluded.embedding, exemplars.embedding),
                    status = excluded.status
                """, (
                    exemplar["id"], exemplar["question"], exemplar["answer"],
                    exemplar.get("category", "general"), exemplar.get("language", "en"),
                    emb_str,
                    exemplar.get("times_selected", 0), exemplar.get("successful_rescues", 0),
                    exemplar.get("failed_rescues", 0), exemplar.get("win_rate", 0.0),
                    exemplar.get("quality_score", 0.0), exemplar.get("impact_score", 0.0),
                    exemplar.get("status", "active"),
                    exemplar.get("created_at", now), exemplar.get("last_used_at")
                ))
                conn.commit()

    def get_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute("SELECT * FROM exemplars WHERE status = ? ORDER BY quality_score DESC", (status,))
                else:
                    cursor.execute("SELECT * FROM exemplars ORDER BY quality_score DESC")
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    if item.get("embedding"):
                        item["embedding"] = json.loads(item["embedding"])
                    results.append(item)
                return results

    def update_stats(self, exemplar_id: str, success: bool) -> None:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT times_selected, successful_rescues, failed_rescues FROM exemplars WHERE id = ?", (exemplar_id,))
                row = cursor.fetchone()
                if not row:
                    return
                times_selected = row["times_selected"] + 1
                successful = row["successful_rescues"] + (1 if success else 0)
                failed = row["failed_rescues"] + (0 if success else 1)
                win_rate = successful / times_selected if times_selected > 0 else 0.0
                # Bayesian smoothed score (prior mean 0.5, weight 5)
                quality_score = (successful + 2.5) / (times_selected + 5.0)

                cursor.execute("""
                UPDATE exemplars SET
                    times_selected = ?,
                    successful_rescues = ?,
                    failed_rescues = ?,
                    win_rate = ?,
                    quality_score = ?,
                    last_used_at = ?
                WHERE id = ?
                """, (times_selected, successful, failed, win_rate, quality_score, now, exemplar_id))
                conn.commit()

    def update_status(self, exemplar_id: str, status: str) -> None:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE exemplars SET status = ? WHERE id = ?", (status, exemplar_id))
                conn.commit()

    def delete(self, exemplar_id: str) -> None:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM exemplars WHERE id = ?", (exemplar_id,))
                conn.commit()

    # --- RequestLogStore Methods ---
    def log_request(self, log_entry: Dict[str, Any]) -> None:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO request_logs (
                    request_id, session_id, timestamp, mode, model_id, rung,
                    input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
                    tokens_saved, tokens_saved_actual, tokens_saved_estimated,
                    is_estimated_tokens, llm_calls_avoided,
                    cost_usd, baseline_cost_usd, saving_pct,
                    cache_hit, cache_type, similarity, latency_ms, prefix_hash,
                    judge_score, judge_verdict,
                    execution_path, node_states, node_details, timeline
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_entry["request_id"], log_entry["session_id"],
                    log_entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    log_entry.get("mode", "kifayat"), log_entry.get("model_id", "mock"),
                    log_entry.get("rung", 1),
                    log_entry.get("input_tokens", 0), log_entry.get("output_tokens", 0),
                    log_entry.get("cache_read_tokens", 0), log_entry.get("cache_write_tokens", 0),
                    log_entry.get("tokens_saved", 0),
                    log_entry.get("tokens_saved_actual", 0),
                    log_entry.get("tokens_saved_estimated", 0),
                    1 if log_entry.get("is_estimated_tokens") else 0,
                    log_entry.get("llm_calls_avoided", 0),
                    log_entry.get("cost_usd", 0.0),
                    log_entry.get("baseline_cost_usd", 0.0), log_entry.get("saving_pct", 0.0),
                    1 if log_entry.get("cache_hit") else 0,
                    log_entry.get("cache_type"), log_entry.get("similarity"),
                    log_entry.get("latency_ms", 0.0), log_entry.get("prefix_hash"),
                    log_entry.get("judge_score"), log_entry.get("judge_verdict"),
                    json.dumps(log_entry.get("execution_path", [])),
                    json.dumps(log_entry.get("node_states", {})),
                    json.dumps(log_entry.get("node_details", {})),
                    json.dumps(log_entry.get("timeline", []))
                ))
                conn.commit()

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM request_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    if item.get("execution_path") and isinstance(item["execution_path"], str):
                        try:
                            item["execution_path"] = json.loads(item["execution_path"])
                        except Exception:
                            pass
                    if item.get("node_states") and isinstance(item["node_states"], str):
                        try:
                            item["node_states"] = json.loads(item["node_states"])
                        except Exception:
                            pass
                    if item.get("node_details") and isinstance(item["node_details"], str):
                        try:
                            item["node_details"] = json.loads(item["node_details"])
                        except Exception:
                            pass
                    if item.get("timeline") and isinstance(item["timeline"], str):
                        try:
                            item["timeline"] = json.loads(item["timeline"])
                        except Exception:
                            pass
                    results.append(item)
                return results

    def get_request_log(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM request_logs WHERE request_id = ?", (request_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                item = dict(row)
                for key in ["execution_path", "node_states", "node_details", "timeline"]:
                    if item.get(key) and isinstance(item[key], str):
                        try:
                            item[key] = json.loads(item[key])
                        except Exception:
                            pass
                return item

    def get_filtered_logs(
        self,
        limit: int = 50,
        filter_type: Optional[str] = None,
        search_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM request_logs WHERE 1=1"
                params: List[Any] = []

                if search_id:
                    query += " AND request_id LIKE ?"
                    params.append(f"%{search_id.strip()}%")

                if filter_type == "cache_hit":
                    query += " AND cache_hit = 1"
                elif filter_type == "cache_miss":
                    query += " AND cache_hit = 0"
                elif filter_type == "rung_1":
                    query += " AND rung = 1"
                elif filter_type == "rung_2":
                    query += " AND rung = 2"
                elif filter_type == "rung_3":
                    query += " AND rung = 3"
                elif filter_type == "failed":
                    query += " AND judge_score < 3"

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                results = []
                for r in rows:
                    item = dict(r)
                    for key in ["execution_path", "node_states", "node_details", "timeline"]:
                        if item.get(key) and isinstance(item[key], str):
                            try:
                                item[key] = json.loads(item[key])
                            except Exception:
                                pass
                    results.append(item)
                return results

    def get_token_savings_series(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT
                    request_id,
                    timestamp,
                    (input_tokens + output_tokens) as tokens_used,
                    tokens_saved,
                    tokens_saved_actual,
                    tokens_saved_estimated,
                    is_estimated_tokens,
                    (input_tokens + output_tokens + tokens_saved) as baseline_tokens,
                    (baseline_cost_usd - cost_usd) as cost_saved_usd,
                    cache_hit,
                    rung
                FROM request_logs
                ORDER BY timestamp ASC
                LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [dict(r) for r in rows]

    def get_cache_analytics(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT
                    COUNT(*) as total_cache_lookups,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits,
                    SUM(CASE WHEN cache_hit = 0 THEN 1 ELSE 0 END) as cache_misses,
                    AVG(CASE WHEN cache_hit = 1 THEN latency_ms ELSE NULL END) as avg_hit_latency_ms,
                    AVG(CASE WHEN cache_hit = 0 THEN latency_ms ELSE NULL END) as avg_miss_latency_ms,
                    SUM(CASE WHEN cache_hit = 1 THEN tokens_saved ELSE 0 END) as cache_saved_tokens,
                    SUM(CASE WHEN cache_hit = 1 THEN (baseline_cost_usd - cost_usd) ELSE 0 END) as cache_cost_saved_usd,
                    SUM(CASE WHEN cache_hit = 1 THEN llm_calls_avoided ELSE 0 END) as avoided_calls
                FROM request_logs
                """)
                summary = dict(cursor.fetchone())

                cursor.execute("SELECT COUNT(*) as total_entries, SUM(hit_count) as total_entry_hits FROM semantic_cache")
                cache_row = cursor.fetchone()
                summary["cache_entries_stored"] = cache_row["total_entries"] or 0
                summary["cache_entries_hits"] = cache_row["total_entry_hits"] or 0

                total_lookups = (summary["cache_hits"] or 0) + (summary["cache_misses"] or 0)
                summary["cache_hit_rate"] = ((summary["cache_hits"] or 0) / total_lookups) if total_lookups > 0 else 0.0
                return summary

    def get_exemplar_analytics(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT
                    COUNT(*) as total_exemplars,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_exemplars,
                    SUM(CASE WHEN status = 'candidate_for_pruning' THEN 1 ELSE 0 END) as candidate_for_pruning,
                    SUM(times_selected) as total_selections,
                    SUM(successful_rescues) as total_rescues,
                    SUM(failed_rescues) as total_failures,
                    AVG(win_rate) as average_win_rate,
                    AVG(quality_score) as average_quality_score
                FROM exemplars
                """)
                stats = dict(cursor.fetchone())

                cursor.execute("""
                SELECT id, question, category, language, times_selected, successful_rescues,
                       failed_rescues, win_rate, quality_score, status, last_used_at
                FROM exemplars
                ORDER BY times_selected DESC, quality_score DESC
                LIMIT 15
                """)
                stats["top_exemplars"] = [dict(r) for r in cursor.fetchall()]

                # Rung 2 rescue stats from logs
                cursor.execute("""
                SELECT
                    SUM(CASE WHEN rung = 2 THEN 1 ELSE 0 END) as rung2_attempts,
                    SUM(CASE WHEN rung = 2 AND judge_score >= 3 THEN 1 ELSE 0 END) as rung2_successes,
                    SUM(CASE WHEN rung = 3 THEN 1 ELSE 0 END) as rung3_escalations
                FROM request_logs
                """)
                r2_stats = dict(cursor.fetchone())
                stats["rung2_attempts"] = r2_stats["rung2_attempts"] or 0
                stats["rung2_successes"] = r2_stats["rung2_successes"] or 0
                stats["rung2_rescue_rate"] = (
                    (stats["rung2_successes"] / stats["rung2_attempts"])
                    if stats["rung2_attempts"] > 0 else 1.0
                )
                return stats

    def get_memory_analytics(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT session_id, raw_turns, frozen_blocks, merged_blocks, turn_count FROM sessions")
                rows = cursor.fetchall()
                total_sessions = len(rows)
                total_raw_turns = 0
                total_frozen_blocks = 0
                total_merged_blocks = 0
                raw_turn_tokens = 0
                frozen_tokens = 0
                merged_tokens = 0

                for r in rows:
                    raw_turns = json.loads(r["raw_turns"])
                    frozen = json.loads(r["frozen_blocks"])
                    merged = json.loads(r["merged_blocks"])
                    total_raw_turns += len(raw_turns)
                    total_frozen_blocks += len(frozen)
                    total_merged_blocks += len(merged)

                    for t in raw_turns:
                        raw_turn_tokens += len(t.get("user", "").split()) + len(t.get("assistant", "").split())
                    for b in frozen:
                        frozen_tokens += len(b.get("summary", "").split())
                    for m in merged:
                        merged_tokens += len(m.get("summary", "").split())

                total_compressed_tokens = raw_turn_tokens + frozen_tokens + merged_tokens
                # Uncompressed turns would have retained all previous turns verbatim
                uncompressed_est = (total_raw_turns + total_frozen_blocks * 6) * 120
                saved_tokens = max(0, uncompressed_est - total_compressed_tokens)

                return {
                    "total_sessions": total_sessions,
                    "total_raw_turns": total_raw_turns,
                    "total_frozen_blocks": total_frozen_blocks,
                    "total_merged_blocks": total_merged_blocks,
                    "raw_turn_tokens": raw_turn_tokens,
                    "frozen_block_tokens": frozen_tokens,
                    "merged_summary_tokens": merged_tokens,
                    "total_memory_tokens": total_compressed_tokens,
                    "estimated_uncompressed_tokens": uncompressed_est,
                    "memory_tokens_saved": saved_tokens,
                    "context_reduction_pct": round((saved_tokens / uncompressed_est * 100.0), 2) if uncompressed_est > 0 else 0.0
                }

    def get_metrics_summary(self) -> Dict[str, Any]:
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT
                    COUNT(*) as total_requests,
                    COUNT(DISTINCT session_id) as total_conversations,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits,
                    SUM(CASE WHEN cache_hit = 0 THEN 1 ELSE 0 END) as cache_misses,
                    SUM(tokens_saved) as total_tokens_saved,
                    SUM(tokens_saved_actual) as tokens_saved_actual,
                    SUM(tokens_saved_estimated) as tokens_saved_estimated,
                    SUM(llm_calls_avoided) as total_llm_calls_avoided,
                    SUM(baseline_cost_usd - cost_usd) as total_cost_saved_usd,
                    AVG(latency_ms) as average_latency_ms,
                    SUM(CASE WHEN rung = 3 THEN 1 ELSE 0 END) as strong_model_calls,
                    SUM(CASE WHEN rung IN (1, 2) THEN 1 ELSE 0 END) as cheap_model_calls,
                    SUM(CASE WHEN rung = 2 THEN 1 ELSE 0 END) as rung2_rescues,
                    SUM(cost_usd) as actual_cost_usd,
                    SUM(baseline_cost_usd) as baseline_cost_usd,
                    SUM(input_tokens + output_tokens) as total_tokens_used
                FROM request_logs
                """)
                summary = dict(cursor.fetchone())

                # Active exemplars count
                cursor.execute("SELECT COUNT(*) as count FROM exemplars WHERE status = 'active'")
                summary["active_exemplars"] = cursor.fetchone()["count"]

                # Memory blocks count
                cursor.execute("SELECT raw_turns, frozen_blocks, merged_blocks FROM sessions")
                rows = cursor.fetchall()
                total_frozen = 0
                total_merged = 0
                for r in rows:
                    total_frozen += len(json.loads(r["frozen_blocks"]))
                    total_merged += len(json.loads(r["merged_blocks"]))
                summary["total_blocks_frozen"] = total_frozen
                summary["total_blocks_merged"] = total_merged

                total_reqs = summary["total_requests"] or 0
                cache_hits = summary["cache_hits"] or 0
                summary["cache_hit_rate"] = (cache_hits / total_reqs) if total_reqs > 0 else 0.0
                baseline = summary["baseline_cost_usd"] or 0.0
                actual = summary["actual_cost_usd"] or 0.0
                summary["savings_pct"] = (((baseline - actual) / baseline) * 100.0) if baseline > 0 else 0.0
                cheap = summary["cheap_model_calls"] or 0
                strong = summary["strong_model_calls"] or 0
                summary["repair_success_rate"] = (cheap / (cheap + strong)) if (cheap + strong) > 0 else 1.0

                return summary
