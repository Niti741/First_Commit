import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from backend.app.providers.base import LLMProvider, ProviderResponse, ProviderUsage, JudgeResult

logger = logging.getLogger("kifayat.providers.router")


class ProviderHealth:
    """Tracks provider operational status, error rates, and circuit breaker state."""
    def __init__(self, name: str, cost_per_1k_tokens: float = 0.0015):
        self.name = name
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.consecutive_failures: int = 0
        self.total_calls: int = 0
        self.total_failures: int = 0
        self.last_failure_time: float = 0.0
        self.circuit_open: bool = False
        self.cooldown_seconds: float = 30.0

    def record_success(self):
        self.consecutive_failures = 0
        self.circuit_open = False
        self.total_calls += 1

    def record_failure(self):
        self.total_calls += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()
        # Open circuit breaker after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.circuit_open = True
            logger.warning(f"Circuit breaker TRIPPED for provider '{self.name}'. Cool-down for {self.cooldown_seconds}s.")

    def is_available(self) -> bool:
        if not self.circuit_open:
            return True
        # Check if cooldown has elapsed
        if time.time() - self.last_failure_time > self.cooldown_seconds:
            logger.info(f"Circuit breaker HALF-OPEN for provider '{self.name}'. Attempting recovery.")
            return True
        return False


class MultiProviderRouter(LLMProvider):
    """
    Intelligent Multi-Provider Router with Failover & Cost Arbitration.
    Orchestrates Primary (e.g. NVIDIA NIM / Custom User Key) and Fallback Providers (Bedrock / Mock).
    """

    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        priority_order: Optional[List[str]] = None
    ):
        self.providers = providers
        self.priority_order = priority_order or list(providers.keys())
        self.health: Dict[str, ProviderHealth] = {
            name: ProviderHealth(name=name) for name in self.providers.keys()
        }

    @property
    def provider_name(self) -> str:
        return "multi_provider_router"

    @property
    def supports_prompt_caching(self) -> bool:
        # Returns True if active primary provider supports caching
        primary_name = self.priority_order[0] if self.priority_order else None
        if primary_name and primary_name in self.providers:
            return self.providers[primary_name].supports_prompt_caching
        return True

    def get_provider_status(self) -> Dict[str, Any]:
        """Returns health diagnostics and failover readiness across all providers."""
        status = {}
        for name, h in self.health.items():
            status[name] = {
                "available": h.is_available(),
                "circuit_open": h.circuit_open,
                "consecutive_failures": h.consecutive_failures,
                "total_calls": h.total_calls,
                "total_failures": h.total_failures
            }
        return status

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        model_id: Optional[str] = None
    ) -> ProviderResponse:
        """Executes generation with automatic failover across priority providers."""
        last_error = None
        for name in self.priority_order:
            provider = self.providers.get(name)
            health = self.health.get(name)
            if not provider or (health and not health.is_available()):
                logger.info(f"Skipping provider '{name}' (unavailable or circuit open).")
                continue

            try:
                res = await provider.generate(
                    messages=messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_id=model_id
                )
                if health:
                    health.record_success()
                primary_name = self.priority_order[0] if self.priority_order else None
                if name != primary_name:
                    res.fallback_used = True
                return res
            except Exception as e:
                logger.error(f"Provider '{name}' failed during generate: {e}. Initiating failover.")
                if health:
                    health.record_failure()
                last_error = e

        raise RuntimeError(f"All configured providers failed in MultiProviderRouter. Last error: {last_error}")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        model_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Streams tokens from the healthiest provider with failover."""
        for name in self.priority_order:
            provider = self.providers.get(name)
            health = self.health.get(name)
            if not provider or (health and not health.is_available()):
                continue

            try:
                stream_started = False
                async for chunk in provider.stream(
                    messages=messages,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_id=model_id
                ):
                    stream_started = True
                    yield chunk
                if health:
                    health.record_success()
                return
            except Exception as e:
                logger.error(f"Provider '{name}' streaming failed: {e}. Attempting failover.")
                if health:
                    health.record_failure()
                if stream_started:
                    yield f"\n[Stream interrupted on provider '{name}', failing over...]"
                    break

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Embedding generation with failover."""
        for name in self.priority_order:
            provider = self.providers.get(name)
            health = self.health.get(name)
            if not provider or (health and not health.is_available()):
                continue

            try:
                embeddings = await provider.embed(texts)
                if health:
                    health.record_success()
                return embeddings
            except Exception as e:
                logger.warning(f"Embedding failed on provider '{name}': {e}. Falling over.")
                if health:
                    health.record_failure()

        # Final local fallback
        from backend.app.providers.mock_provider import MockProvider
        mock = MockProvider()
        return await mock.embed(texts)

    async def judge(
        self,
        question: str,
        answer: str,
        context: str,
        model_id: Optional[str] = None
    ) -> JudgeResult:
        """Evaluates answer quality with failover to rule judge."""
        for name in self.priority_order:
            provider = self.providers.get(name)
            health = self.health.get(name)
            if not provider or (health and not health.is_available()):
                continue

            try:
                result = await provider.judge(
                    question=question,
                    answer=answer,
                    context=context,
                    model_id=model_id
                )
                if health:
                    health.record_success()
                return result
            except Exception as e:
                logger.warning(f"Judge failed on provider '{name}': {e}. Falling over.")
                if health:
                    health.record_failure()

        from backend.app.providers.mock_provider import MockProvider
        mock = MockProvider()
        return await mock.judge(question, answer, context)
