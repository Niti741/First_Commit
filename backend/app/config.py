import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "local"
    PROJECT_NAME: str = "Kifayat"
    APP_ID: str = "assistant"
    APPLICATION_VERSION: str = "2.0.0"
    HANDBOOK_NAME: str = "Kifayat AI General Knowledge Base"
    HANDBOOK_VERSION: str = "2.0.0"
    HANDBOOK_PATH: str = "backend/data/handbook.md"
    SEED_EXEMPLARS_PATH: str = "backend/data/seed_exemplars.json"
    SQLITE_DB_PATH: str = "backend/kifayat.db"

    # Provider & Model Settings
    LLM_PROVIDER: str = "mock"  # 'mock', 'nvidia', or 'bedrock'
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    
    CHEAP_MODEL_ID: str = "meta/llama-3.2-11b-vision-instruct"
    STRONG_MODEL_ID: str = "meta/llama-3.2-11b-vision-instruct"
    JUDGE_MODEL_ID: str = "meta/llama-3.2-11b-vision-instruct"

    AWS_REGION: str = "us-east-1"

    # Memory Settings
    RAW_WINDOW_TURNS: int = 3
    BLOCK_TURNS: int = 6
    BLOCKS_PER_MERGE: int = 5
    MAX_MEMORY_TOKENS: int = 4000

    # Semantic Cache Settings
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.90
    SEMANTIC_CACHE_TTL: int = 86400
    SEMANTIC_CACHE_MAX_ENTRIES: int = 10000

    # Compaction Settings
    COMPACTION_ENABLED: bool = True
    COMPACTION_QUEUE_TYPE: str = "local"  # 'local' or 'sqs'

    # Exemplar Settings
    MAX_EXEMPLARS: int = 500
    EXEMPLAR_MIN_EVALUATIONS: int = 5
    EXEMPLAR_STALE_DAYS: int = 90
    EXEMPLAR_TOP_K: int = 3

    # Generation Limits
    MAX_OUTPUT_TOKENS: int = 2048
    MAX_QUESTION_LENGTH: int = 4000
    STREAMING_ENABLED: bool = True

    # Modes supported: baseline, naive, cache_only, kifayat
    MODES: str = "baseline,cache_only,naive,kifayat"

    # Costs (USD per 1k tokens)
    COST_CHEAP_INPUT: float = 0.00015
    COST_CHEAP_OUTPUT: float = 0.00060
    COST_STRONG_INPUT: float = 0.00180
    COST_STRONG_OUTPUT: float = 0.00540
    COST_CACHE_READ: float = 0.00003  # ~80% discount for prompt cache read
    COST_CACHE_WRITE: float = 0.00015
    
    BUDGET_ALERT: float = 20.0

    @property
    def supported_modes(self) -> List[str]:
        return [m.strip() for m in self.MODES.split(",")]


settings = Settings()
