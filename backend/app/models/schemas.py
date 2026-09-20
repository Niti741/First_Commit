from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # 'system', 'user', 'assistant'
    content: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 500
    session_id: Optional[str] = None
    mode: Optional[str] = "kifayat"  # 'baseline', 'naive', 'cache_only', 'kifayat'


class KifayatReceipt(BaseModel):
    request_id: str
    session_id: str
    model_id: str
    rung: int  # 0 (cache), 1 (cheap), 2 (cheap+exemplars), 3 (strong fallback)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    tokens_saved: int = 0
    tokens_saved_actual: int = 0
    tokens_saved_estimated: int = 0
    is_estimated_tokens: bool = False
    llm_calls_avoided: int = 0
    cost_usd: float = 0.0
    baseline_cost_usd: float = 0.0
    saving_pct: float = 0.0
    cache_hit: bool = False
    cache_type: Optional[str] = None  # 'semantic' or None
    similarity: Optional[float] = None
    latency_ms: float = 0.0
    prefix_hash: Optional[str] = None
    judge_score: Optional[int] = None
    judge_verdict: Optional[str] = None
    intent: str = "UNKNOWN"
    routing_reason: Optional[str] = None
    provider: str = "nvidia"
    provider_request_sent: bool = True
    provider_response_received: bool = True
    fallback_used: bool = False
    ttft_ms: Optional[float] = None
    mode: str = "kifayat"
    execution_path: List[str] = Field(default_factory=list)
    node_states: Dict[str, str] = Field(default_factory=dict)
    node_details: Dict[str, Any] = Field(default_factory=dict)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: Optional[Dict[str, Any]] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: ChatUsage
    kifayat_receipt: KifayatReceipt


class FeedbackRequest(BaseModel):
    request_id: str
    question: str
    answer: str
    thumbs_up: bool
    app_id: Optional[str] = "helpdesk"
    session_id: Optional[str] = None
    category: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
    message: str
    promoted_to_exemplar: bool = False
    exemplar_id: Optional[str] = None


class ExemplarItem(BaseModel):
    id: str
    question: str
    answer: str
    category: str
    language: str = "en"
    times_selected: int = 0
    successful_rescues: int = 0
    failed_rescues: int = 0
    win_rate: float = 0.0
    quality_score: float = 0.0
    impact_score: float = 0.0
    status: str = "active"  # 'active', 'candidate_for_pruning', 'archived'
    created_at: str
    last_used_at: Optional[str] = None


class DashboardStats(BaseModel):
    total_requests: int
    total_conversations: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    total_tokens_saved: int
    total_cost_saved_usd: float
    average_latency_ms: float
    strong_model_calls: int
    cheap_model_calls: int
    repair_success_rate: float
    actual_cost_usd: float
    baseline_cost_usd: float
    savings_pct: float
    active_exemplars: int
    total_blocks_frozen: int
    total_blocks_merged: int
