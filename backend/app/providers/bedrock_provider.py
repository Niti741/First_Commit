"""
Future AWS Bedrock LLM Provider Adapter.
Allows switching from NVIDIA to Amazon Bedrock (Claude 3.5 Sonnet, Titan Embeddings)
via `LLM_PROVIDER=bedrock` without changing business or context logic.
"""
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.providers.base import LLMProvider, ProviderResponse, ProviderUsage, JudgeResult


class BedrockProvider(LLMProvider):
    def __init__(self, region: str = "us-east-1", default_model: str = "anthropic.claude-3-5-sonnet-20240620-v1:0"):
        self.region = region
        self.default_model = default_model

    @property
    def provider_name(self) -> str:
        return "bedrock"

    @property
    def supports_prompt_caching(self) -> bool:
        return True

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        model_id: Optional[str] = None
    ) -> ProviderResponse:
        raise NotImplementedError("BedrockProvider will activate when deployed to AWS.")

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        model_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        raise NotImplementedError("BedrockProvider streaming will activate in AWS environment.")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError("BedrockProvider embed will activate in AWS environment.")

    async def judge(
        self,
        question: str,
        answer: str,
        context: str,
        model_id: Optional[str] = None
    ) -> JudgeResult:
        raise NotImplementedError("BedrockProvider judge will activate in AWS environment.")
