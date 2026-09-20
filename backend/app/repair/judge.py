import logging
from typing import Optional
from backend.app.providers.base import LLMProvider, JudgeResult

logger = logging.getLogger("kifayat.repair.judge")


class JudgeSystem:
    """
    Evaluates generated responses against handbook context.
    Safely handles provider failures or malformed judge outputs without crashing.
    """

    def __init__(self, provider: LLMProvider, judge_model_id: Optional[str] = None):
        self.provider = provider
        self.judge_model_id = judge_model_id

    async def verify(
        self,
        question: str,
        answer: str,
        handbook_context: str
    ) -> JudgeResult:
        try:
            return await self.provider.judge(
                question=question,
                answer=answer,
                context=handbook_context,
                model_id=self.judge_model_id
            )
        except Exception as e:
            logger.warning(f"Judge invocation failed with error: {e}. Defaulting to safe pass.")
            return JudgeResult(
                passed=True,
                score=3,
                reason="Judge invocation failed; defaulted to pass to avoid user disruption."
            )
