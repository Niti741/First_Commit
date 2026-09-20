import time
import logging
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel

from backend.app.config import settings
from backend.app.providers.base import LLMProvider, ProviderResponse, JudgeResult
from backend.app.context.builder import ContextBuilder
from backend.app.exemplars.store import ExemplarStore
from backend.app.exemplars.mining import AutonomousExemplarMiner
from backend.app.repair.rule_checks import CheapRuleChecker
from backend.app.repair.judge import JudgeSystem

logger = logging.getLogger("kifayat.repair.ladder")


class LadderResult(BaseModel):
    text: str
    rung: int  # 1 (Cheap), 2 (Cheap+Exemplars), 3 (Strong)
    model_id: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    latency_ms: float
    judge_score: Optional[int] = None
    judge_verdict: Optional[str] = None
    rescued_by_exemplars: bool = False
    used_exemplar_ids: List[str] = []
    fallback_used: bool = False


class PromptRepairLadder:
    """
    Three-Rung Prompt Repair Ladder:
      Rung 1: Cheap Model -> Rule Check -> Judge
      Rung 2: Cheap Model + Retrieved Exemplars -> Rule Check -> Judge
      Rung 3: Strong Model Fallback
    Goal: Maximize answer accuracy and handbook consistency while keeping strong-model calls to an absolute minimum.
    """

    def __init__(
        self,
        provider: LLMProvider,
        context_builder: ContextBuilder,
        exemplar_store: ExemplarStore,
        cheap_model_id: Optional[str] = None,
        strong_model_id: Optional[str] = None,
        judge_model_id: Optional[str] = None,
        router: Optional[Any] = None
    ):
        self.provider = provider
        self.context_builder = context_builder
        self.exemplar_store = exemplar_store
        self.router = router
        
        if router:
            self.cheap_model_id = router.get_model("cheap")
            self.strong_model_id = router.get_model("strong")
            self.judge_model_id = router.get_model("judge")
        else:
            self.cheap_model_id = cheap_model_id or settings.CHEAP_MODEL_ID
            self.strong_model_id = strong_model_id or settings.STRONG_MODEL_ID
            self.judge_model_id = judge_model_id or settings.JUDGE_MODEL_ID

        self.judge_system = JudgeSystem(provider, self.judge_model_id)

    async def execute(
        self,
        question: str,
        session_context: Dict[str, Any],
        query_embedding: Optional[List[float]] = None,
        mode: str = "kifayat",
        is_conversational: bool = False,
        maximum_rung: int = 3
    ) -> LadderResult:
        start_time = time.perf_counter()

        raw_turns = session_context.get("raw_turns", [])
        frozen_blocks = session_context.get("frozen_blocks", [])
        merged_blocks = session_context.get("merged_blocks", [])

        # --- Baseline / Naive / Cache-Only Mode bypasses repair ladder ---
        if mode in ["baseline", "naive", "cache_only"]:
            prompt_data = self.context_builder.build_prompt(
                current_question=question,
                recent_raw_turns=raw_turns,
                frozen_blocks=frozen_blocks,
                merged_blocks=merged_blocks,
                mode=mode
            )
            model_to_use = self.strong_model_id if mode == "baseline" else self.cheap_model_id
            resp = await self.provider.generate(
                messages=prompt_data["messages"],
                system=prompt_data["system"],
                model_id=model_to_use
            )
            total_latency = (time.perf_counter() - start_time) * 1000
            return LadderResult(
                text=resp.text,
                rung=1 if mode != "baseline" else 3,
                model_id=resp.usage.model_id,
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
                cache_read_tokens=resp.usage.cache_read_tokens,
                cache_write_tokens=resp.usage.cache_write_tokens,
                latency_ms=round(total_latency, 2),
                judge_score=5,
                judge_verdict="Bypassed ladder in mode: " + mode,
                fallback_used=getattr(resp, "fallback_used", False)
            )

        # =========================================================================
        # PATH A / RUNG 1: CONVERSATIONAL OR CHEAP MODEL GENERATION
        # =========================================================================
        if is_conversational or maximum_rung == 1:
            rung1_prompt = self.context_builder.build_conversational_prompt(
                current_question=question,
                recent_raw_turns=raw_turns
            )
            rung1_resp = await self.provider.generate(
                messages=rung1_prompt["messages"],
                system=rung1_prompt["system"],
                model_id=self.cheap_model_id
            )
            total_latency = (time.perf_counter() - start_time) * 1000
            return LadderResult(
                text=rung1_resp.text,
                rung=1,
                model_id=rung1_resp.usage.model_id,
                input_tokens=rung1_resp.usage.input_tokens,
                output_tokens=rung1_resp.usage.output_tokens,
                cache_read_tokens=rung1_resp.usage.cache_read_tokens,
                cache_write_tokens=rung1_resp.usage.cache_write_tokens,
                latency_ms=round(total_latency, 2),
                judge_score=5,
                judge_verdict="Conversational intent verified on Rung 1",
                fallback_used=getattr(rung1_resp, "fallback_used", False)
            )

        # =========================================================================
        # RUNG 1: CHEAP MODEL GENERATION & VERIFICATION (KNOWLEDGE / TASK)
        # =========================================================================
        rung1_prompt = self.context_builder.build_prompt(
            current_question=question,
            recent_raw_turns=raw_turns,
            frozen_blocks=frozen_blocks,
            merged_blocks=merged_blocks,
            exemplars=None,
            mode=mode
        )

        rung1_resp = await self.provider.generate(
            messages=rung1_prompt["messages"],
            system=rung1_prompt["system"],
            model_id=self.cheap_model_id
        )

        # Rule check
        rule_passed, rule_reason = CheapRuleChecker.check_answer(rung1_resp.text, question=question)
        is_handbook_query = any(
            w in question.lower() for w in [
                "hostel", "fee", "fees", "mess", "attendance", "placement", "curfew", "scholarship",
                "admission", "campus", "college", "kit", "kifayat institute", "semester", "cgpa",
                "grade", "faculty", "exam", "course"
            ]
        )

        if rule_passed:
            # If not a campus handbook query, Rung 1 response is valid and complete; return immediately
            if not is_handbook_query:
                total_latency = (time.perf_counter() - start_time) * 1000
                return LadderResult(
                    text=rung1_resp.text,
                    rung=1,
                    model_id=rung1_resp.usage.model_id,
                    input_tokens=rung1_resp.usage.input_tokens,
                    output_tokens=rung1_resp.usage.output_tokens,
                    cache_read_tokens=rung1_resp.usage.cache_read_tokens,
                    cache_write_tokens=rung1_resp.usage.cache_write_tokens,
                    latency_ms=round(total_latency, 2),
                    judge_score=5,
                    judge_verdict="Direct generation verified via structural checks",
                    fallback_used=getattr(rung1_resp, "fallback_used", False)
                )

            judge_res = await self.judge_system.verify(
                question=question,
                answer=rung1_resp.text,
                handbook_context=self.context_builder.canonical_handbook
            )
            # Support both 0.0-1.0 and 1.0-5.0 score scales
            norm_score = (judge_res.score * 5.0) if judge_res.score <= 1.0 else float(judge_res.score)
            if judge_res.passed and norm_score >= 3.0:
                total_latency = (time.perf_counter() - start_time) * 1000
                return LadderResult(
                    text=rung1_resp.text,
                    rung=1,
                    model_id=rung1_resp.usage.model_id,
                    input_tokens=rung1_resp.usage.input_tokens,
                    output_tokens=rung1_resp.usage.output_tokens,
                    cache_read_tokens=rung1_resp.usage.cache_read_tokens,
                    cache_write_tokens=rung1_resp.usage.cache_write_tokens,
                    latency_ms=round(total_latency, 2),
                    judge_score=round(norm_score),
                    judge_verdict=judge_res.reason,
                    fallback_used=getattr(rung1_resp, "fallback_used", False)
                )
            else:
                logger.info(f"Rung 1 failed judge verification: {judge_res.reason} (score={norm_score}). Escalating to Rung 2.")
        else:
            logger.info(f"Rung 1 failed cheap rule check: {rule_reason}. Escalating to Rung 2.")

        # =========================================================================
        # RUNG 2: CHEAP MODEL + RETRIEVED EXEMPLARS
        # =========================================================================
        if query_embedding is None:
            embeddings = await self.provider.embed([question])
            query_embedding = embeddings[0]

        exemplars = await self.exemplar_store.retrieve(query_embedding, top_k=settings.EXEMPLAR_TOP_K)
        used_exemplar_ids = [ex["id"] for ex in exemplars]

        rung2_prompt = self.context_builder.build_prompt(
            current_question=question,
            recent_raw_turns=raw_turns,
            frozen_blocks=frozen_blocks,
            merged_blocks=merged_blocks,
            exemplars=exemplars,
            mode=mode
        )

        rung2_resp = await self.provider.generate(
            messages=rung2_prompt["messages"],
            system=rung2_prompt["system"],
            model_id=self.cheap_model_id
        )

        rung2_rule_passed, _ = CheapRuleChecker.check_answer(rung2_resp.text, question=question)
        if rung2_rule_passed:
            rung2_judge = await self.judge_system.verify(
                question=question,
                answer=rung2_resp.text,
                handbook_context=self.context_builder.canonical_handbook
            )
            norm_score_2 = (rung2_judge.score * 5.0) if rung2_judge.score <= 1.0 else float(rung2_judge.score)
            if rung2_judge.passed and norm_score_2 >= 3.0:
                # Registered rescue win for used exemplars
                for ex_id in used_exemplar_ids:
                    self.exemplar_store.record_outcome(ex_id, success=True)

                total_latency = (time.perf_counter() - start_time) * 1000
                return LadderResult(
                    text=rung2_resp.text,
                    rung=2,
                    model_id=rung2_resp.usage.model_id,
                    input_tokens=rung1_resp.usage.input_tokens + rung2_resp.usage.input_tokens,
                    output_tokens=rung2_resp.usage.output_tokens,
                    cache_read_tokens=rung2_resp.usage.cache_read_tokens,
                    cache_write_tokens=rung2_resp.usage.cache_write_tokens,
                    latency_ms=round(total_latency, 2),
                    judge_score=round(norm_score_2),
                    judge_verdict=rung2_judge.reason,
                    rescued_by_exemplars=True,
                    used_exemplar_ids=used_exemplar_ids,
                    fallback_used=getattr(rung1_resp, "fallback_used", False) or getattr(rung2_resp, "fallback_used", False)
                )
            else:
                for ex_id in used_exemplar_ids:
                    self.exemplar_store.record_outcome(ex_id, success=False)
                logger.info(f"Rung 2 failed judge: {rung2_judge.reason}. Escalating to Rung 3.")
        else:
            for ex_id in used_exemplar_ids:
                self.exemplar_store.record_outcome(ex_id, success=False)
            logger.info("Rung 2 failed rule checks. Escalating to Rung 3.")

        # If maximum_rung capped at 2, return Rung 2 response without escalating
        if maximum_rung <= 2:
            total_latency = (time.perf_counter() - start_time) * 1000
            return LadderResult(
                text=rung2_resp.text,
                rung=2,
                model_id=rung2_resp.usage.model_id,
                input_tokens=rung1_resp.usage.input_tokens + rung2_resp.usage.input_tokens,
                output_tokens=rung2_resp.usage.output_tokens,
                cache_read_tokens=rung2_resp.usage.cache_read_tokens,
                cache_write_tokens=rung2_resp.usage.cache_write_tokens,
                latency_ms=round(total_latency, 2),
                judge_score=3,
                judge_verdict="Capped at maximum_rung=2",
                rescued_by_exemplars=False,
                used_exemplar_ids=used_exemplar_ids,
                fallback_used=getattr(rung1_resp, "fallback_used", False) or getattr(rung2_resp, "fallback_used", False)
            )

        # =========================================================================
        # RUNG 3: STRONG MODEL FALLBACK
        # =========================================================================
        rung3_prompt = self.context_builder.build_prompt(
            current_question=question,
            recent_raw_turns=raw_turns,
            frozen_blocks=frozen_blocks,
            merged_blocks=merged_blocks,
            exemplars=None,
            mode=mode
        )

        rung3_resp = await self.provider.generate(
            messages=rung3_prompt["messages"],
            system=rung3_prompt["system"],
            model_id=self.strong_model_id
        )

        # Autonomous Active Learning: asynchronously mine (question, strong_answer) for future Rung 2 rescue
        try:
            asyncio.create_task(
                AutonomousExemplarMiner.mine_candidate(
                    question=question,
                    answer=rung3_resp.text,
                    provider=self.provider,
                    exemplar_store=self.exemplar_store
                )
            )
        except Exception as e:
            logger.warning(f"Could not schedule autonomous exemplar mining: {e}")

        total_latency = (time.perf_counter() - start_time) * 1000
        return LadderResult(
            text=rung3_resp.text,
            rung=3,
            model_id=rung3_resp.usage.model_id,
            input_tokens=rung1_resp.usage.input_tokens + rung3_resp.usage.input_tokens,
            output_tokens=rung3_resp.usage.output_tokens,
            cache_read_tokens=rung3_resp.usage.cache_read_tokens,
            cache_write_tokens=rung3_resp.usage.cache_write_tokens,
            latency_ms=round(total_latency, 2),
            judge_score=5,
            judge_verdict="Strong model fallback invoked.",
            fallback_used=getattr(rung1_resp, "fallback_used", False) or getattr(rung3_resp, "fallback_used", False)
        )
