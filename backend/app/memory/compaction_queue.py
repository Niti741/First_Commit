import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
from backend.app.memory.block_manager import BlockManager
from backend.app.memory.hierarchical import HierarchicalMemoryMerger
from backend.app.storage.base import SessionStore

logger = logging.getLogger("kifayat.compaction")


class CompactionQueue(ABC):
    @abstractmethod
    async def push_event(self, event: Dict[str, Any]) -> None:
        pass


class LocalCompactionQueue(CompactionQueue):
    """
    In-memory async worker queue for local development.
    Processes compaction tasks in the background without delaying chat responses.
    Ensures idempotency using (conversation_id, block_id, compaction_version).
    """

    def __init__(self, session_store: SessionStore):
        self.session_store = session_store
        self.block_manager = BlockManager()
        self.hierarchical_merger = HierarchicalMemoryMerger()
        self.queue: asyncio.Queue = asyncio.Queue()
        self._processed_events: Set[str] = set()
        self._worker_task: Optional[asyncio.Task] = None
        self.stats = {
            "triggered": 0,
            "queued": 0,
            "completed": 0,
            "failed": 0,
            "total_latency_ms": 0.0,
            "history": []
        }

    def start(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Local compaction background worker started.")

    async def stop(self):
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def push_event(self, event: Dict[str, Any]) -> None:
        """
        Pushes compaction event containing only metadata:
        event_type, conversation_id, block_id, compaction_version, timestamp
        """
        self.stats["triggered"] += 1
        self.stats["queued"] += 1
        await self.queue.put(event)

    def get_metrics(self) -> Dict[str, Any]:
        """Returns compaction metrics for observability dashboard."""
        completed = self.stats["completed"]
        avg_lat = (self.stats["total_latency_ms"] / completed) if completed > 0 else 0.0
        return {
            "compactions_triggered": self.stats["triggered"],
            "compactions_queued": self.stats["queued"],
            "compactions_completed": completed,
            "compactions_failed": self.stats["failed"],
            "average_compaction_latency_ms": round(avg_lat, 2),
            "recent_events": self.stats["history"][-20:]
        }

    async def _worker_loop(self):
        while True:
            try:
                event = await self.queue.get()
                t0 = datetime.now(timezone.utc).timestamp()
                try:
                    await self._process_event(event)
                    lat_ms = (datetime.now(timezone.utc).timestamp() - t0) * 1000.0
                    self.stats["completed"] += 1
                    self.stats["total_latency_ms"] += lat_ms
                    self.stats["history"].append({
                        "conversation_id": event.get("conversation_id"),
                        "block_id": event.get("block_id"),
                        "status": "COMPLETED",
                        "latency_ms": round(lat_ms, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as ex:
                    self.stats["failed"] += 1
                    self.stats["history"].append({
                        "conversation_id": event.get("conversation_id"),
                        "block_id": event.get("block_id"),
                        "status": "FAILED",
                        "error": str(ex),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    raise ex
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing compaction event: {e}")

    async def _process_event(self, event: Dict[str, Any]) -> None:
        conv_id = event.get("conversation_id")
        block_id = event.get("block_id")
        version = event.get("compaction_version", 1)

        # Idempotency check
        idempotency_key = f"{conv_id}:{block_id}:{version}"
        if idempotency_key in self._processed_events:
            logger.info(f"Duplicate compaction event skipped: {idempotency_key}")
            return

        session_data = self.session_store.get_session(conv_id)
        if not session_data:
            return

        # Check if block is already present in frozen_blocks
        existing_blocks = session_data.get("frozen_blocks", [])
        if any(b.get("block_id") == block_id for b in existing_blocks):
            self._processed_events.add(idempotency_key)
            return

        pending_block_data = event.get("block_data")
        if not pending_block_data:
            return

        # 1. Summarize and freeze block
        frozen_block = self.block_manager.create_frozen_block_summary(pending_block_data)
        existing_blocks.append(frozen_block)
        session_data["frozen_blocks"] = existing_blocks

        # 2. Check for hierarchical merge
        merged_blocks = session_data.get("merged_blocks", [])
        merge_result = self.hierarchical_merger.check_and_merge(existing_blocks, merged_blocks)
        session_data["frozen_blocks"] = merge_result["frozen_blocks"]
        session_data["merged_blocks"] = merge_result["merged_blocks"]

        # 3. Persist updated session
        self.session_store.save_session(conv_id, session_data)
        self._processed_events.add(idempotency_key)
        logger.info(f"Compacted and froze Block #{block_id} for session {conv_id}")


class SQSCompactionQueue(CompactionQueue):
    """
    Future AWS Adapter: Pushes metadata message to Amazon SQS for asynchronous Lambda consumption.
    """
    def __init__(self, queue_url: str = "", region: str = "us-east-1"):
        self.queue_url = queue_url
        self.region = region

    async def push_event(self, event: Dict[str, Any]) -> None:
        raise NotImplementedError("SQSCompactionQueue will activate when deployed to AWS.")
