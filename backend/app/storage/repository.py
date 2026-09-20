from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import time
import uuid


# =========================================================================
# Domain Models (Ready for MongoDB BSON and SQL ORM / SQLite)
# =========================================================================

class User(BaseModel):
    id: str = Field(default_factory=lambda: f"usr-{uuid.uuid4().hex[:12]}")
    email: Optional[str] = None
    full_name: Optional[str] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    created_at: float = Field(default_factory=time.time)
    last_login_at: Optional[float] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: f"sess-{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = "anonymous"
    title: str = "New Conversation"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    is_pinned: bool = False
    is_archived: bool = False
    mode: str = "kifayat"
    turn_count: int = 0


class Message(BaseModel):
    id: str = Field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:12]}")
    conversation_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    receipt_id: Optional[str] = None
    tokens: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)


class UserPreferences(BaseModel):
    user_id: str
    theme: str = "dark"
    default_mode: str = "kifayat"
    custom_instructions: Optional[str] = None
    auto_run_canvas: bool = True
    stream_enabled: bool = True


class MemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: f"mem-{uuid.uuid4().hex[:12]}")
    user_id: str
    key: str
    value: str
    confidence: float = 1.0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class FeedbackItem(BaseModel):
    id: str = Field(default_factory=lambda: f"fb-{uuid.uuid4().hex[:12]}")
    request_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = "anonymous"
    thumbs_up: bool
    comment: Optional[str] = None
    created_at: float = Field(default_factory=time.time)


class UsageRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"usg-{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None
    model_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    tokens_saved: int = 0
    cost_usd: float = 0.0
    timestamp: float = Field(default_factory=time.time)


# =========================================================================
# Abstract Repository Interfaces (Data Access Layer)
# =========================================================================

class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def create_user(self, user: User) -> User:
        pass

    @abstractmethod
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[User]:
        pass


class IConversationRepository(ABC):
    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        pass

    @abstractmethod
    async def list_conversations(self, user_id: Optional[str] = None, limit: int = 50) -> List[Conversation]:
        pass

    @abstractmethod
    async def save_conversation(self, conversation: Conversation) -> None:
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        pass


class IMessageRepository(ABC):
    @abstractmethod
    async def get_messages(self, conversation_id: str, limit: int = 100) -> List[Message]:
        pass

    @abstractmethod
    async def add_message(self, message: Message) -> Message:
        pass


class IPreferencesRepository(ABC):
    @abstractmethod
    async def get_preferences(self, user_id: str) -> UserPreferences:
        pass

    @abstractmethod
    async def update_preferences(self, preferences: UserPreferences) -> None:
        pass


class IMemoryRepository(ABC):
    @abstractmethod
    async def get_memories(self, user_id: str) -> List[MemoryItem]:
        pass

    @abstractmethod
    async def set_memory(self, memory: MemoryItem) -> None:
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str) -> bool:
        pass


class IFeedbackRepository(ABC):
    @abstractmethod
    async def save_feedback(self, feedback: FeedbackItem) -> None:
        pass

    @abstractmethod
    async def get_feedback_stats(self) -> Dict[str, Any]:
        pass


class IUsageRepository(ABC):
    @abstractmethod
    async def log_usage(self, usage: UsageRecord) -> None:
        pass

    @abstractmethod
    async def get_usage_summary(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        pass


# =========================================================================
# Concrete SQLite Implementation (Active Storage Bridge)
# =========================================================================

class SQLiteRepositoryManager:
    """
    Unified manager wrapping SQLiteStore with domain models.
    Can be replaced transparently with MongoRepositoryManager.
    """

    def __init__(self, store: Any):
        self.store = store

    async def get_or_create_conversation(self, session_id: str, user_id: str = "anonymous") -> Conversation:
        sess = self.store.get_session(session_id)
        if sess:
            return Conversation(
                id=session_id,
                user_id=user_id,
                title=f"Session {session_id[:8]}",
                turn_count=sess.get("turn_count", 0)
            )
        conv = Conversation(id=session_id, user_id=user_id)
        self.store.save_session(session_id, {
            "session_id": session_id,
            "raw_turns": [],
            "frozen_blocks": [],
            "merged_blocks": [],
            "turn_count": 0
        })
        return conv

    async def list_conversations(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.store.list_sessions(limit=limit)

    async def save_feedback(self, req_id: str, thumbs_up: bool, comment: Optional[str] = None) -> None:
        fb = FeedbackItem(request_id=req_id, thumbs_up=thumbs_up, comment=comment)
        self.store.save_feedback(fb.model_dump())
