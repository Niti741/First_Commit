import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class RequestExecutionTracer:
    """
    Tracks real-time execution path, micro-timestamps, and component node states
    for the interactive Kifayat Workflow & Analytics visualizer.
    """

    NODE_IDS = [
        "request_validate",
        "semantic_cache",
        "context_builder",
        "memory_retrieval",
        "exemplar_search",
        "cheap_model",
        "judge",
        "rung2_exemplars",
        "judge_rung2",
        "rung3_strong",
        "final_response",
        "stream_user",
        "async_compaction",
        "memory_update",
        "exemplar_feedback",
        "self_pruning"
    ]

    def __init__(self, request_id: str, session_id: str):
        self.request_id = request_id
        self.session_id = session_id
        self.start_perf = time.perf_counter()
        self.start_utc = datetime.now(timezone.utc).isoformat()
        
        self.timeline: List[Dict[str, Any]] = []
        self.node_states: Dict[str, str] = {node_id: "WAITING" for node_id in self.NODE_IDS}
        self.node_details: Dict[str, Dict[str, Any]] = {node_id: {} for node_id in self.NODE_IDS}
        self.execution_path: List[str] = []

    def _current_offset_ms(self) -> float:
        return round((time.perf_counter() - self.start_perf) * 1000.0, 2)

    def record_event(
        self,
        component: str,
        event: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Records a timestamped event into the execution timeline."""
        offset_ms = self._current_offset_ms()
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3],
            "offset_ms": offset_ms,
            "component": component,
            "event": event,
            "details": details or {}
        }
        self.timeline.append(entry)

    def set_node_state(
        self,
        node_id: str,
        state: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Updates the execution state of a workflow node:
        'WAITING', 'RUNNING', 'COMPLETED', 'SKIPPED', 'FAILED', 'CACHE HIT'
        """
        if node_id in self.node_states:
            self.node_states[node_id] = state
            if node_id not in self.execution_path and state in ["RUNNING", "COMPLETED", "CACHE HIT"]:
                self.execution_path.append(node_id)
        if details:
            self.node_details.setdefault(node_id, {}).update(details)

    def export(self) -> Dict[str, Any]:
        """Returns the full execution trace package."""
        total_latency_ms = self._current_offset_ms()
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "start_time": self.start_utc,
            "total_latency_ms": total_latency_ms,
            "execution_path": self.execution_path,
            "node_states": self.node_states,
            "node_details": self.node_details,
            "timeline": self.timeline
        }
