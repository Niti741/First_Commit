from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class SemanticCache(ABC):
    @abstractmethod
    async def get_similar(
        self,
        question: str,
        embedding: List[float],
        namespace: str,
        threshold: float = 0.90
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def set(
        self,
        question: str,
        answer: str,
        embedding: List[float],
        namespace: str,
        context_hash: str,
        ttl: int = 86400
    ) -> str:
        pass

    @abstractmethod
    async def delete(self, cache_id: str) -> None:
        pass

    @abstractmethod
    async def invalidate(self, namespace: Optional[str] = None) -> int:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        pass
