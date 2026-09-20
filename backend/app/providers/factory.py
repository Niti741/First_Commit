import os
from backend.app.config import settings
from backend.app.providers.base import LLMProvider
from backend.app.providers.mock_provider import MockProvider
from backend.app.providers.nvidia_provider import NVIDIAProvider
from backend.app.providers.bedrock_provider import BedrockProvider


_provider_instance = None


def get_llm_provider(handbook_text: str = "") -> LLMProvider:
    """
    Returns the configured LLM provider instance.
    Defaults to MockProvider if no NVIDIA API key is configured or if LLM_PROVIDER=mock.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.LLM_PROVIDER.lower().strip()

    if provider_name == "nvidia":
        if not settings.NVIDIA_API_KEY:
            _provider_instance = MockProvider(handbook_text=handbook_text)
        else:
            from backend.app.providers.router import MultiProviderRouter
            primary_nvidia = NVIDIAProvider(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
                default_model=settings.NVIDIA_MODEL
            )
            fallback_mock = MockProvider(handbook_text=handbook_text)
            _provider_instance = MultiProviderRouter(
                providers={"nvidia_primary": primary_nvidia, "fallback_local": fallback_mock},
                priority_order=["nvidia_primary", "fallback_local"]
            )
    elif provider_name == "bedrock":
        _provider_instance = BedrockProvider(region=settings.AWS_REGION)
    else:
        _provider_instance = MockProvider(handbook_text=handbook_text)

    return _provider_instance


class ProviderFactory:
    @staticmethod
    def get_provider(handbook_text: str = "") -> LLMProvider:
        return get_llm_provider(handbook_text)

