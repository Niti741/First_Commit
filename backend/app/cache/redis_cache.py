"""
Future AWS Redis/Valkey Semantic Cache Adapter.
Enables distributed low-latency caching with Valkey/Redis on AWS ElastiCache
without changing the gateway API or ContextBuilder.
"""
from typing import Dict, List, Optional, Any
from backend.app.cache.base import SemanticCache


class RedisSemanticCache(SemanticCache):
    def __init__(self, host: str = "localhost", port: int = 6379, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.password = password

    async def get_similar(
        self,
        question: str,
        embedding: List[float],
        namespace: str,
        threshold: float = 0.90
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("RedisSemanticCache will activate when deployed to AWS/ElastiCache.")

    async def set(
        self,
        question: str,
        answer: str,
        embedding: List[float],
        namespace: str,
        context_hash: str,
        ttl: int = 86400
    ) -> str:
        raise NotImplementedError("RedisSemanticCache will activate when deployed to AWS.")

    async def delete(self, cache_id: str) -> None:
        raise NotImplementedError("RedisSemanticCache will activate when deployed to AWS.")

    async def invalidate(self, namespace: Optional[str] = None) -> int:
        raise NotImplementedError("RedisSemanticCache will activate when deployed to AWS.")

    async def clear(self) -> None:
        raise NotImplementedError("RedisSemanticCache will activate when deployed to AWS.")

    async def stats(self) -> Dict[str, Any]:
        raise NotImplementedError("RedisSemanticCache will activate when deployed to AWS.")
