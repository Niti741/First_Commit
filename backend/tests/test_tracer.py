import pytest
from backend.app.tracing.tracer import RequestExecutionTracer


def test_tracer_lifecycle():
    tracer = RequestExecutionTracer(request_id="req-test-123", session_id="sess-test-456")
    tracer.record_event("api", "Request received", {"length": 25})
    tracer.set_node_state("request_validate", "COMPLETED", {"language": "en"})
    tracer.set_node_state("semantic_cache", "CACHE HIT", {"similarity": 0.94, "lookup_ms": 3.2})
    tracer.set_node_state("cheap_model", "SKIPPED")

    data = tracer.export()
    assert data["request_id"] == "req-test-123"
    assert data["session_id"] == "sess-test-456"
    assert len(data["timeline"]) >= 1
    assert data["node_states"]["request_validate"] == "COMPLETED"
    assert data["node_states"]["semantic_cache"] == "CACHE HIT"
    assert data["node_states"]["cheap_model"] == "SKIPPED"
    assert data["node_details"]["semantic_cache"]["similarity"] == 0.94
    assert "request_validate" in data["execution_path"]
