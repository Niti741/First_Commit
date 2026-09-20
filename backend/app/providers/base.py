from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel


class ProviderUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    latency_ms: float = 0.0
    model_id: str = ""


class ProviderResponse(BaseModel):
    text: str
    usage: ProviderUsage
    raw: Optional[Dict[str, Any]] = None
    fallback_used: bool = False


class JudgeResult(BaseModel):
    passed: bool
    score: float = 1.0  # 0.0 - 1.0 normalized score or 1-5 scale
    issues: List[str] = []
    reason: str = ""


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def supports_prompt_caching(self) -> bool:
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        model_id: Optional[str] = None
    ) -> ProviderResponse:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        model_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    async def judge(
        self,
        question: str,
        answer: str,
        context: str,
        model_id: Optional[str] = None
    ) -> JudgeResult:
        pass
